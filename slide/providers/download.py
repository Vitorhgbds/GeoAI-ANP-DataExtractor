from concurrent.futures import Future, ThreadPoolExecutor
from os import PathLike
from pathlib import Path
from typing import Any, Callable
import aiohttp
import asyncio
from aiohttp.http_exceptions import ContentLengthError

from slide.logger import Logger
from slide.providers.cache import CacheProvider
from slide.providers.progress import ProgressProvider, ProgressType


logger = Logger().get_logger()

class DownloadProvider:
    def __init__(self, *args, **kwargs) -> None:
        self.progress_provider = ProgressProvider()
        self.downloaded_urls: list[str] = []
    
    def download(
        self
        ,urls: list[str]
        ,directory: Path	
        ,headers: dict[str, str] | None = None
        ,fetch_directory_callback: Callable[[str],  PathLike] | None = None
        ,use_cache: bool = False
        ,cache_path: PathLike = Path(".cache.json")
                 ) -> None:
        
        self.downloaded_urls: list = []
        self.cache = CacheProvider(cache_path)
        if use_cache:
            logger.debug(f"Loading urls from cache.")
            content = self.cache.fetch()
            self.downloaded_urls = content.get("downloaded_urls", [])
        else:
            self.cache.clean()
            
        urls_to_download = set(urls).difference(set(self.downloaded_urls))
        if not urls_to_download:
            logger.debug(f"No urls to download.")
            return
        
        step_progress = self.progress_provider.get_progress(ProgressType.STEP_TIMED)
        live = self.progress_provider.get_live()
        with live:
            step_task_id = step_progress.add_task('', total=len(urls_to_download), action=f'Downloading sources in {str(directory)}')
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
                            headers, 
                            step_task_id,
                            4, # Num parts 
                            1024 * 1024 * 2, # Chunk size
                        )
                    )
        for future in futures:
            future.result()
        step_progress.stop_task(step_task_id)
        
        self.cache.save({"downloaded_urls": self.downloaded_urls})
                
    def run_parallel_download(
        self,
        url: str, 
        file: Path,  
        headers: dict[str, Any], 
        progress_step_task_id,
        num_parts: int = 4, 
        chunk_size: int = 1024,
        ) -> str:
        max_retries = 10
        retries = 0
        while retries < max_retries:
            try:
                asyncio.run(self.parallel_download(
                    url, 
                    file, 
                    headers, 
                    progress_step_task_id,
                    num_parts, 
                    chunk_size
                ))
                self.downloaded_urls.append(url)
                return url            
            except Exception as e:
                logger.error(e)
                logger.warning(f"Retrying number: {retries} of maximum {max_retries}")
                retries = retries + 1 
                self.cache.save({"downloaded_urls": self.downloaded_urls})
    
    
    async def parallel_download(
        self,
        url: str, 
        file: Path, 
        headers: dict[str, Any], 
        progress_step_task_id,
        num_parts: int = 4, 
        chunk_size: int = 1024 * 1024):
        """Splits a file download into parallel parts for faster speed."""
        
        async with aiohttp.ClientSession() as session:
            async with session.head(url, headers=headers) as response:
                total_size = int(response.headers.get("content-length", 0))
                logger.info(f"Downloading {url} → {file}")
                logger.info(f"Total size: {total_size}")
                supports_range = response.headers.get("Accept-Ranges", "none").lower() == "bytes"
                
        if not supports_range:
            logger.warning(f"Server does not support range requests, downloading file in a single part")
        else:
            logger.debug(f"Server supports range requests, downloading file in {num_parts} parts")
        num_parts = total_size // chunk_size if supports_range else 1
        chunk_size = chunk_size if supports_range and chunk_size < total_size else total_size
        
        queue = asyncio.Queue()  # Queue to store chunks

        download_progress = self.progress_provider.get_progress(ProgressType.DOWNLOAD)
        download_task_id = download_progress.add_task('', filename=file.name, total=total_size)
        
        with open(file, "wb") as f:
            f.truncate(total_size)  # Pre-allocate file space

        tasks = []

        # Start chunk downloads
        for i in range(num_parts):
            start = i * chunk_size
            end = (start + chunk_size - 1) if i < num_parts - 1 else total_size

            tasks.append(asyncio.create_task(self.download_chunk(url, start, end, queue, headers)))

        # Start writer process
        writer_task = asyncio.create_task(self.write_chunks_to_file(file, queue, total_size, download_task_id))

        await asyncio.gather(*tasks)  # Wait for downloads
        await queue.join()  # Wait for all chunks to be written
        writer_task.cancel()  # Stop the writer task
        download_progress.stop_task(download_task_id)
        download_progress.update(download_task_id,visible=False)

        step_progress = self.progress_provider.get_progress(ProgressType.STEP_TIMED)
        step_progress.update(progress_step_task_id,advance=1)
        return url
    
    async def download_chunk(
        self,
        url: str, 
        start: int, 
        end: int, 
        queue: asyncio.Queue, 
        headers: dict[str, Any]):
        """Downloads a specific chunk of a file and puts it in a queue."""
        chunk_headers = headers.copy()
        chunk_headers["Range"] = f"bytes={start}-{end}"

        retries = 0
        max_retries = 10
        while retries < max_retries:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(1800)) as session:
                    async with session.get(url, headers=chunk_headers) as response:
                        logger.debug(f"Response status: {response.content}")
                        logger.debug(f"Downloading chunk: {url} [{start}-{end}]")
                        logger.debug(f"Response length: {response.content_length}")
                        chunk = await response.read()
                        logger.debug(f"Downloaded chunk: {url} [{start}-{end}]")
                        await queue.put((start, chunk))
                retries = max_retries
            except ContentLengthError as e:
                logger.error(f"Chunk download failed: {url} [{start}-{end}] → {e}")
                retries += 1
                logger.warning(f"Retrying chunk download: {retries}")
            except Exception as e:
                logger.exception(e)
                retries += 1
                logger.warning(f"Failed to download chunk retrying: {retries}")

    async def write_chunks_to_file(self, file, queue: asyncio.Queue, total_size: int, download_task_id):
        """Writes chunks from queue to file as they arrive."""
        download_progress = self.progress_provider.get_progress(ProgressType.DOWNLOAD)
        with open(file, "r+b") as f:
            while total_size > 0:
                start, chunk = await queue.get()
                f.seek(start)
                f.write(chunk)
                download_progress.update(download_task_id, advance=len(chunk))
                total_size -= len(chunk)
                queue.task_done()

    

    