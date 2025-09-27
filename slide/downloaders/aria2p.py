import json
from pathlib import Path
import subprocess
import time
import aria2p
import socket
from slide.database.models.download import DownloadDAO, DownloadDTO, DownloadStatus
from slide.downloaders.downloadPolicy import DownloadPolicy
from slide.logger import Logger
from slide.providers.progress import ProgressProvider, ProgressType, TaskID
import traceback

logging = Logger()
logger = logging.get_logger()
progress = ProgressProvider()
download_progress = progress.get_progress(ProgressType.DOWNLOAD)
tasks: dict[str, TaskID] = {}
class Aria2P(DownloadPolicy):
    def __init__(self, overwrite: bool = False, rpc_port: int = 6800, cache_dao: DownloadDAO | None = None):
        self.rpc_port = rpc_port
        self.aria2c_process = None
        self.aria2: aria2p.API | None = None
        self.cache: DownloadDAO = cache_dao if cache_dao else DownloadDAO()
        self.downloads_monitoring_process = None
        self.overwrite = overwrite

    def start_aria2c(self) -> aria2p.API:
        # Start aria2c with RPC enabled
        self.aria2c_process = subprocess.Popen([
            "aria2c",
            "--enable-rpc",
            "--rpc-listen-all=true",
            "--rpc-allow-origin-all",
            f"--rpc-listen-port={self.rpc_port}",
            "--max-connection-per-server=16",
            "--split=16",
            "--min-split-size=1M",
            "--continue=true",
            "--dir=downloads",  # default download folder
            "--max-download-result=16000",   # allow tracking 15k+ completed downloads
            "--quiet=true"
        ])
        self.__wait_for_server_ready(timeout=15)

        client = aria2p.Client(host="http://localhost", port=self.rpc_port)
        return aria2p.API(client)

    def download(self, dtos: list[DownloadDTO]) -> list[str]:
        
        if not self.aria2:
            self.aria2 = self.start_aria2c()

        downloads = []
        download_r = []
        while len(dtos) > 0:
            try:
                for file in dtos:
                    headers = json.loads(file.headers) if file.headers else {}
                    header_list = [f"{k}: {v}" for k, v in headers.items()] if isinstance(headers, dict) else []
                    if not self.overwrite and (Path(file.path) / file.name).exists():
                        dtos.remove(file)
                        continue
                    download = self.aria2.add_uris([file.url], options={"header": header_list, "dir": str(file.path), "out": file.name, "pause": True})
                    downloads.append(download)
                    download_r.append(download.name)
                    #tasks[download.name] = download_progress.add_task(f"{file.name}", filename=file.name, total=100)
                    dtos.remove(file)
            except Exception as e:
                # Retry adding the download after a short delay
                logger.error(f"Error while adding download: {e}")
                time.sleep(1)
                continue
        self.aria2.resume_all()
        self.wait_monitor_downloads()
        return download_r

    def wait_monitor_downloads(self):
        if not self.aria2:
            self.aria2 = self.start_aria2c()

        downloads = self.aria2.get_downloads()
        logger.info(f"Tracking {len(downloads)} downloads...")
        #download_progress.start()
        while len(downloads) > 0:
            try:
                downloads = self.aria2.get_downloads()
                for d in downloads:
                    #t = tasks[d.name]
                    #download_progress.update(t, completed=d.progress, total=100, speed=d.download_speed, refresh=True)
                    is_finished = self.__update_download_status(d)
                    if is_finished:
                        #download_progress.remove_task(t)
                        self.aria2.remove([d])
                        downloads.remove(d)
            except Exception as e:
                logger.error(f"Error while updating download status: {traceback.format_exc()}\n {e}\n")
                time.sleep(1)
                continue

            # Check if all downloads are finished
            if all([d.is_complete or d.has_failed for d in downloads]):
                break
            time.sleep(0.5)  # Polling interval
        #download_progress.stop()
        logger.info("[✅] All downloads finished.")
        
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
        errors: dict | None = {'status': d.error_code, 'message': d.error_message} if d.has_failed else None
        if dto:
            dto.status = status
            dto.errors = json.dumps(errors)
            self.cache.upsert(dto)
        else:
            self.cache.bulk_insert([DownloadDTO(
                url=self.aria2.client.get_uris(d.gid).get("uri", ""),
                path=str(d.dir),
                name=d.name,
                status=status,
                errors=json.dumps(errors) if errors else None,
            )])
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
