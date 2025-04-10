from os import PathLike
from pathlib import Path
from typing import Any, Callable
from concurrent.futures import Future, ThreadPoolExecutor
import aiohttp
import asyncio
import signal
import json

from slide.logger import Logger
from slide.providers.cache import CacheProvider
from slide.providers.progress import ProgressProvider, ProgressType


logger = Logger().get_logger()

class DownloadProvider:
    def __init__(self, num_parts: int = 4, chunk_size: int = 1024 * 1024 * 2, *args, **kwargs) -> None:
        self.progress_provider = ProgressProvider()
        self.current_task_id: int
        self.downloaded_urls: list[str] = []
        self.download_errors: list[dict] = []
        self.urls: list[str] = []
        self.paths: list[Path] = []
        self.num_parts = num_parts
        self.chunk_size = chunk_size
        self.SENTINEL = object()
    
    def download(
        self
        ,urls: list[str]
        ,directory: Path	
        ,headers: dict[str, str] | None = None
        ,fetch_directory_callback: Callable[[str],  PathLike] | None = None
        ,use_cache: bool = False
        ,cache_path: PathLike = Path(".cache.json")
                 ) -> list[Path]:
        files_path = []
        self.downloaded_urls: list = []
        self.cache = CacheProvider(cache_path)
        if use_cache:
            logger.debug(f"Loading urls from cache.")
            content = self.cache.fetch()
            self.downloaded_urls = content.get("downloaded_urls", [])
            self.urls = content.get("urls", [])
            self.paths = [Path(p) for p in content.get("paths", [])]
            self.downloaded_errors = content.get("errors", [])
        else:
            self.cache.clean()
        all_urls = set(urls + self.urls)
        urls_to_download = all_urls.difference(set(self.downloaded_urls))
        if not urls_to_download:
            logger.debug(f"Difference between given urls and downloaded urls is empty.")
            return self.paths
        
        step_progress = self.progress_provider.get_progress(ProgressType.STEP_TIMED)
        live = self.progress_provider.get_live()
        with live:
            self.current_task_id = step_progress.add_task('', total=len(urls_to_download), action=f'Downloading sources in {str(directory)}')
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures: list[Future] = []
                for link in urls_to_download:
                    file: Path = (
                        directory / fetch_directory_callback(link)
                        if fetch_directory_callback
                        else directory / Path(link.split("/")[-1])
                        )
                    file.parent.mkdir(parents=True, exist_ok=True)
                    
                    futures.append(
                        executor.submit(
                            self.run_parallel_download,
                            link,
                            file, 
                            headers
                        )
                    )
        for future in futures:
            file = future.result()
            if file:
                self.paths.append(file)
        
        step_progress.remove_task(self.current_task_id)
        unique_urls = set(self.downloaded_urls)
        unique_paths = set(self.paths)
        unique_errors = [dict(t) for t in {tuple(sorted(d.items())) for d in self.download_errors}]
        self.cache.save({"urls": list(all_urls), "downloaded_urls": list(unique_urls), "paths":[str(p) for p in unique_paths], "errors": unique_errors})
        return self.paths
                
    def run_parallel_download(
        self,
        url: str, 
        file: Path,  
        headers: dict[str, Any], 
        ) -> Path:
        try:
            asyncio.run(self.parallel_download(
                url, 
                file, 
                headers,  
            ))
            self.downloaded_urls.append(url)
            step_progress = self.progress_provider.get_progress(ProgressType.STEP_TIMED)
            step_progress.update(self.current_task_id,advance=1)
        except Exception as e:
            e.add_note(f"Error downloading file: {url}")
            logger.error(e)
            self.download_errors.append({"url": url, "error": str(e)})
        return file            
    
    async def parallel_download(
        self,
        url: str, 
        file: Path, 
        headers: dict[str, Any]
        ) -> str:
        """Splits a file download into parallel parts for faster speed."""
        
        async with aiohttp.ClientSession() as session:
            async with session.head(url, headers=headers) as response:
                total_size = int(response.headers.get("content-length", 0))
                supports_range = response.headers.get("Accept-Ranges", "none").lower() == "bytes"
                logger.debug(f"Supports range: {supports_range}")
                
        chunk_size = self.chunk_size if self.chunk_size < total_size else total_size
        num_parts = total_size // chunk_size if chunk_size < total_size else 1
    
        with open(file, "wb") as f:
            f.truncate(total_size)  # Pre-allocate file space

        download_progress = self.progress_provider.get_progress(ProgressType.DOWNLOAD)
        download_task_id = download_progress.add_task(f'', filename=file.name, total=total_size)
        # Start chunk downloads
        tasks = [] # List of tasks
        queue = asyncio.Queue()  # Queue to store chunks
        for i in range(num_parts):
            start = i * chunk_size
            end = (start + chunk_size - 1) if i < num_parts - 1 else total_size
            tasks.append(asyncio.create_task(self.download_chunk(url, start, end, queue, headers, end==total_size)))
        # Start writer process
        writer_task = asyncio.create_task(self.write_chunks_to_file(file, queue, total_size, download_task_id))

        await asyncio.gather(*tasks)  # Wait for downloads
        await queue.put(self.SENTINEL)
        await queue.join()  # Wait for all chunks to be written
        # Now safely wait for writer to finish
        actual_size = await writer_task
        
        download_progress.stop_task(download_task_id)
        download_progress.update(download_task_id,visible=False)
        download_progress.remove_task(download_task_id)

        with open(file, "r+b") as f:
            f.truncate(actual_size)
        return url
    
    async def download_chunk(
        self,
        url: str, 
        start: int, 
        end: int, 
        queue: asyncio.Queue, 
        headers: dict[str, Any],
        last_chunk: bool):
        """Downloads a specific chunk of a file and puts it in a queue."""
        chunk_headers = headers.copy()
        chunk_headers["Connection"] = "keep-alive"
        
        current = start
        attempt_end = end
        whole_chunk = b""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(1800)) as session:
            while current < end:
                try:
                    chunk_headers["Range"] = f"bytes={current}-{attempt_end}"
                    async with session.get(url, headers=chunk_headers) as response:
                        chunk = await response.read()
                        whole_chunk += chunk
                        await queue.put((current, chunk))
                        current += len(chunk)
                        attempt_end = min(end, current + (end - current))
                except Exception as e:
                    e.add_note(f"Error downloading chunk: {url} from {start} to {end}")
                    self.download_errors.append({"url": url, "error": str(e)})
                    logger.error(e)
                    if (attempt_end - current) <= 1:
                        break
                    if last_chunk:
                        attempt_end = min(end, current + ((attempt_end - current) // 2))
        
    async def write_chunks_to_file(self, file, queue: asyncio.Queue, total_size: int, download_task_id):
        """Writes chunks from queue to file as they arrive."""
        download_progress = self.progress_provider.get_progress(ProgressType.DOWNLOAD)
        max_offset = 0
        with open(file, "r+b") as f:
            while True:
                item = await queue.get()
                if item == self.SENTINEL:
                    queue.task_done()
                    break
                start, chunk = item
                f.seek(start)
                f.write(chunk)
                # Track how far we wrote
                max_offset = max(max_offset, start + len(chunk))
                download_progress.update(download_task_id, advance=len(chunk))
                queue.task_done()
        return max_offset
    

    