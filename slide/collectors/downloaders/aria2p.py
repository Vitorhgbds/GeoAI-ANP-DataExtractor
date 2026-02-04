import asyncio
import json
from pathlib import Path
import subprocess
import time
import aria2p
import socket
from slide.database.models.download import DownloadDAO, DownloadDTO, DownloadStatus
from slide.collectors.interfaces import DownloadPolicy
from slide.logger import Logger
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

logging = Logger()
logger = logging.get_logger()


class Aria2P(DownloadPolicy):
    def __init__(self, overwrite: bool = False, rpc_port: int = 6800, cache_dao: DownloadDAO | None = None):
        self.rpc_port = rpc_port
        self.aria2c_process = None
        self.aria2: aria2p.API | None = None
        self.cache: DownloadDAO = cache_dao if cache_dao else DownloadDAO()
        self.overwrite = overwrite
        self.errors: dict[str, int] = {}
        self.total_downloads = 0
        self.finished_downloads = 0

    def start_aria2c(self) -> aria2p.API:
        # Start aria2c with RPC enabled
        self.aria2c_process = subprocess.Popen(
            [
                "aria2c",
                "--enable-rpc",
                "--rpc-listen-all=false",
                "--rpc-allow-origin-all",
                f"--rpc-listen-port={self.rpc_port}",
                "--max-connection-per-server=16",
                "--split=16",
                "--min-split-size=1M",
                "--continue=true",
                "--dir=downloads",  # default download folder
                "--max-download-result=16000",  # allow tracking 15k+ completed downloads
                "--quiet=true",
            ]
        )
        self.__wait_for_server_ready(timeout=15)

        client = aria2p.Client(host="http://localhost", port=self.rpc_port)
        return aria2p.API(client)

    def download(self, dtos: list[DownloadDTO]) -> None:
        """Run the download process with async monitoring"""
        self.total_downloads = len(dtos)
        self.finished_downloads = 0
        self.cache.close()

        executor = ThreadPoolExecutor(2)
        loop = asyncio.new_event_loop()

        monitor = loop.run_in_executor(executor, self.monitor_downloads)
        time.sleep(3)  # Give some time for the monitor to start
        download = loop.run_in_executor(executor, self._download_async, dtos)

        try:
            loop.run_until_complete(asyncio.gather(monitor, download, return_exceptions=True))
        except Exception as e:
            logger.error(f"Error occurred during download: {e}")
            self.stop()
            monitor.cancel()
            download.cancel()
        finally:
            loop.close()

    def _download_async(self, dtos: list[DownloadDTO]) -> None:
        if not self.aria2:
            self.aria2 = self.start_aria2c()

        logger.info(f"[🚀] Starting downloads with aria2c (RPC port: {self.rpc_port})...")

        while len(dtos) > 0:
            dto = dtos.pop()

            if not self.overwrite and (Path(dto.path) / dto.name).exists():
                self.total_downloads -= 1
                continue

            headers = json.loads(dto.headers) if dto.headers else {}
            header_list = [f"{k}: {v}" for k, v in headers.items()] if isinstance(headers, dict) else []

            tries = 0
            while True:
                try:
                    download = self.aria2.add_uris(
                        [dto.url], options={"header": header_list, "dir": str(dto.path), "out": dto.name}
                    )
                    tries = 0
                    break  # Exit the loop if the download was added successfully
                except Exception as e:
                    logger.error(f"Error while adding download: {e}")
                    tries += 1
                    if tries >= 10:
                        logger.error(f"Failed to add download for {dto.url} after {tries} attempts. Skipping.")
                        self.total_downloads -= 1
                        break
                    time.sleep(2)

        logger.info(f"Finished adding downloads: {self.total_downloads} total.")

    def monitor_downloads(self):
        if not self.aria2:
            self.aria2 = self.start_aria2c()

        logger.info(f"[ℹ️] Total files to download: {self.total_downloads}")
        logger.info("[ℹ️] Using another terminal run `aria2p top` to monitor each download in real-time.")

        logger.debug("Starting listening to download notifications...")
        self.aria2.listen_to_notifications(
            threaded=True, on_download_error=self.__on_download_error, on_download_complete=self.__on_download_complete
        )

        logger.debug("Starting download monitoring...")

        total_downloads = self.total_downloads
        with tqdm(
            total=self.total_downloads, desc="Downloading files", unit="file", position=0, dynamic_ncols=True
        ) as progress:
            while self.finished_downloads < total_downloads:
                if total_downloads != self.total_downloads:
                    total_downloads = self.total_downloads
                    progress.total = total_downloads
                iterations = self.finished_downloads - progress.n
                progress.update(iterations)
                progress.refresh()

        logger.info("[✅] All downloads finished.")

    def __on_download_complete(self, api: aria2p.API, gid):
        self.cache.ensure_connection()
        logger.debug(f"Download complete for GID: {gid}")
        download = api.get_download(gid)
        self.__update_download_status(download)
        download.purge()
        self.finished_downloads += 1

    def __on_download_error(self, api: aria2p.API, gid):
        self.cache.ensure_connection()
        download = api.get_download(gid)
        summary = "A download failed"
        body = f"{download.name}\n{download.error_message} (code: {download.error_code})."
        # logger.error(f"Download error for GID: {gid}, {body}\n {summary}")
        # pop a desktop notification using notify-send
        # subprocess.call(["notify-send", "-t", "10000", summary, body])
        self.errors[download.name] = self.errors.get(download.name, 0) + 1
        if self.errors[download.name] < 3:
            api.retry_downloads([download])
        else:
            self.__update_download_status(download)
            download.purge()
            self.finished_downloads += 1

    def __update_download_status(self, d: aria2p.Download) -> bool:
        """Update the status of a single download."""
        if not self.aria2:
            self.aria2 = self.start_aria2c()

        is_finished = d.is_complete or d.has_failed
        if not is_finished:
            return is_finished
        uri = d.files[0].uris[0].get("uri", "")
        dto = self.cache.fetch_by_url(uri)
        status = DownloadStatus.DONE.value if d.is_complete else DownloadStatus.WAITING.value
        errors: dict | None = {"status": d.error_code, "message": d.error_message} if d.has_failed else None
        if dto:
            dto.status = status
            dto.errors = json.dumps(errors)
            self.cache.upsert(dto)
        else:
            self.cache.bulk_insert(
                [
                    DownloadDTO(
                        url=self.aria2.client.get_uris(d.gid).get("uri", ""),
                        path=str(d.dir),
                        name=d.name,
                        status=status,
                        errors=json.dumps(errors) if errors else None,
                    )
                ]
            )
        return is_finished

    def __wait_for_server_ready(self, timeout=10, interval=0.5):
        """Waits until the aria2 RPC server is accepting connections."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try opening a socket to the aria2c RPC server
                with socket.create_connection(("localhost", self.rpc_port), timeout=2):
                    return True
            except OSError:
                time.sleep(interval)
        raise TimeoutError("Aria2 RPC server did not become ready in time.")

    def stop(self):
        if self.aria2c_process:
            self.aria2c_process.terminate()
            self.aria2c_process = None
            logger.info("aria2c stopped.")
