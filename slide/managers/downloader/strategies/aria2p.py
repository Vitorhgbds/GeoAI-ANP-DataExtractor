import json
from pathlib import Path
import subprocess
import time
import threading
from typing import List, Dict, Optional
import aria2p
import socket
from rich.progress import (
    Progress,
    TimeElapsedColumn,
    TextColumn,
    SpinnerColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from slide.database.models.download import DownloadDAO, DownloadDTO, DownloadStatus


class Aria2P:
    def __init__(self, rpc_port: int = 6800, cache_dao: DownloadDAO | None = None):
        self.rpc_port = rpc_port
        self.aria2c_process = None
        self.aria2 = None
        self.cache = cache_dao

    def start_aria2c(self):
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
        self._wait_for_server_ready(timeout=15)

        client = aria2p.Client(host="http://localhost", port=self.rpc_port)
        self.aria2 = aria2p.API(client)

    def download(self, dtos: list[DownloadDTO]):
        
        if not self.aria2:
            self.start_aria2c()

        downloads = []
        while len(dtos) > 0:
            try:
                for file in dtos:
                    header_list = [f"{k}: {v}" for k, v in file.headers.items()]
                    download = self.aria2.add_uris([file.url], options={"header": header_list, "dir": str(file.path), "out": file.name})
                    downloads.append(download)
                    dtos.remove(file)
            except Exception as e:
                # Retry adding the download after a short delay
                print(f"[ERROR] Error while adding download: {e}")
                time.sleep(1)
                continue

        self.wait_monitor_downloads()
        return downloads

    def wait_monitor_downloads(self):
        
        downloads = self.aria2.get_downloads()
        print(f"[INFO] Tracking {len(downloads)} downloads...")
        while len(downloads) > 0:
            try:
                downloads = self.aria2.get_downloads()
                for d in downloads:
                    is_finished = self._update_download_status(d)
                    if is_finished:
                        self.aria2.remove([d])
                        downloads.remove(d)
            except Exception as e:
                print(f"[ERROR] Error while updating download status: {e}")
                time.sleep(1)
                continue
                
                
            # Check if all downloads are finished
            if all([d.is_complete or d.has_failed for d in downloads]):
                break
        print("[✅] All downloads finished.")
        
    def _update_download_status(self, d: aria2p.Download) -> bool:
        """Update the status of a single download."""
        is_finished = d.is_complete or d.has_failed
        if not is_finished:
            return is_finished
        uri = d.files[0].uris[0].get("uri", "")
        dto = self.cache.fetch_by_url(uri)
        status = DownloadStatus.DONE if d.is_complete else DownloadStatus.WAITING
        errors = {'status': d.error_code, 'message': d.error_message} if d.has_failed else None
        if dto:
            dto.status = status
            dto.errors = errors
            self.cache.upsert_download(dto)
        else:
            self.cache.bulk_insert([DownloadDTO(
                url=self.aria2.client.get_uris(d.gid).get("uri"),
                path=str(d.dir),
                name=d.name,
                status=status,
                errors=errors
            )])
        return is_finished
    
    def _wait_for_server_ready(self, timeout=10, interval=0.5):
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
            print("[INFO] aria2c stopped.")
