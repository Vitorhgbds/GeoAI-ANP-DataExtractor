import asyncio
from typing import Any
import aiohttp
import pathlib
from concurrent.futures import Future, ThreadPoolExecutor
from slide.logger import Logger
from slide.providers.progress import ProgressProvider, ProgressType

logger = Logger().get_logger()
progress_provider = ProgressProvider()

async def download_chunk(
    url: str, 
    start: int, 
    end: int, 
    queue: asyncio.Queue, 
    headers: dict[str, Any]):
    """Downloads a specific chunk of a file and puts it in a queue."""
    chunk_headers = headers.copy()
    chunk_headers["Range"] = f"bytes={start}-{end}"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(1800)) as session:
        async with session.get(url, headers=chunk_headers) as response:
            chunk = await response.read()
            await queue.put((start, chunk))  # Put chunk in queue for writing

async def write_chunks_to_file(file_path, queue: asyncio.Queue, total_size: int, download_task_id):
    """Writes chunks from queue to file as they arrive."""
    download_progress = progress_provider.get_progress(ProgressType.DOWNLOAD)
    with open(file_path, "r+b") as file:
        while total_size > 0:
            start, chunk = await queue.get()
            file.seek(start)
            file.write(chunk)
            download_progress.update(download_task_id, advance=len(chunk))
            total_size -= len(chunk)
            queue.task_done()

async def parallel_download(
    url: str, 
    directory: pathlib.Path, 
    filename: str, 
    headers: dict[str, Any], 
    task_id, 
    num_parts: int = 4, 
    chunk_size: int = 1024 * 1024):
    """Splits a file download into parallel parts for faster speed."""
    file_path = pathlib.Path(directory) / filename
    pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        async with session.head(url, headers=headers) as response:
            total_size = int(response.headers.get("content-length", 0))

    num_parts = total_size // chunk_size
    
    queue = asyncio.Queue()  # Queue to store chunks
    
    download_progress = progress_provider.get_progress(ProgressType.DOWNLOAD)
    download_task_id = download_progress.add_task('', filename=filename, total=total_size)
    
    with open(file_path, "wb") as file:
        file.truncate(total_size)  # Pre-allocate file space

    tasks = []

    # Start chunk downloads
    for i in range(num_parts):
        start = i * chunk_size
        end = (start + chunk_size - 1) if i < num_parts - 1 else total_size

        tasks.append(asyncio.create_task(download_chunk(url, start, end, queue, headers)))

    # Start writer process
    writer_task = asyncio.create_task(write_chunks_to_file(file_path, queue, total_size, download_task_id))

    await asyncio.gather(*tasks)  # Wait for downloads
    await queue.join()  # Wait for all chunks to be written
    writer_task.cancel()  # Stop the writer task
    download_progress.stop_task(download_task_id)
    download_progress.update(download_task_id,visible=False)

    step_progress = progress_provider.get_progress(ProgressType.STEP_TIMED)
    step_progress.update(task_id,advance=1)

    return file_path

def run_parallel_download(
    url: str, 
    directory: pathlib.Path, 
    filename: str, 
    headers: dict[str, Any], 
    task_id, 
    num_parts: int = 4, 
    chunk_size: int = 1024 * 1024
    ):
    asyncio.run(parallel_download(
        url, 
        directory, 
        filename, 
        headers, 
        task_id, 
        num_parts, 
        chunk_size
    ))

def download_files_concurrently(
    filtered_links: list[str], 
    base_url: str, 
    directory: pathlib.Path,
    basin_name: str, 
    headers: dict[str, Any], 
    data: dict[str,Any]):
    """Handles parallel downloads of multiple files."""
    if not filtered_links:
        logger.debug("No links to download")
        return
    full_path = "/".join(filtered_links[-1].split("/POCO/")[-1].split("/")[:-1])
    step_progress = progress_provider.get_progress(ProgressType.STEP_TIMED)
    step_task_id = step_progress.add_task('', total=len(filtered_links), action=f'Downloading sources in {full_path}')
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures: list[Future] = []
        for link in filtered_links:
            file_url = str(base_url + link)
            file_name = file_url.split("/")[-1]
            file_path = "/".join(file_url.split("/POCO/")[-1].split("/")[:-1])
            full_path = pathlib.Path(directory) / basin_name / file_path
            futures.append(
                executor.submit(
                    run_parallel_download,
                    file_url, 
                    full_path, 
                    file_name, 
                    headers, 
                    step_task_id,
                    4, # Num parts 
                    1024 * 1024 * 2, # Chunk size
                )
            )
        for future in futures:
            future.result()
            #parallel_download(file_url, full_path, file_name, headers=headers, num_parts=4, chunk_size=1024 * 1024 * 2, index=2, progress=progress_bar)
    step_progress.stop_task(step_task_id)
    step_progress.update(step_task_id,visible=False)
        #await asyncio.gather(*tasks)  # Download all files in parallel
