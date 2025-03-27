import os
import pathlib
import re
import requests
from abc import ABC
from bs4 import BeautifulSoup, element
from tqdm.auto import tqdm

from slide.commons import BAR_FORMAT

class Scrapper(ABC):
    
    def matches_patterns(self, text: str, patterns: list[str]) -> bool:
        normalized_text = text.strip()
        matches = [bool(re.search(pattern, normalized_text)) for pattern in patterns]
        return True in matches
    
    def fetch_links(self, content: str, parser: str) -> list[str]:
        soup = BeautifulSoup(content, parser)
        links: list[element.Tag] = soup.find_all('href')
        return [href.text.strip() for href in links]
        
    def download(self, url: str, directory: os.PathLike, filename: str, *args, **kwargs) -> os.PathLike:
        METHOD = kwargs.get("method", "GET")
        HEADERS = kwargs.get("headers")
        PAYLOAD = kwargs.get("data")
        
        response = requests.request(METHOD, url, headers=HEADERS, data=PAYLOAD, stream=True)
    
        if response.status_code != 200:
            raise requests.RequestException(
                f"Error download file from url: {url}"
                f"method: {METHOD}"
                f"headers: {HEADERS}"
                f"data: {PAYLOAD}"
                f"status code: {response.status_code}"
                )
            
        total_size = int(response.headers.get("content-length", 0))
        block_size = 2048
           
        file_path = pathlib.Path(directory) / filename 
        pathlib.Path(directory).mkdir(parents=True, exist_ok=True)
        
        with tqdm(total=total_size, unit="B", unit_scale=True, desc=f"Downloading file",leave=False, position=2) as progress_bar:
            with open(file_path, "wb") as file:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    file.write(data)
        
        if total_size != 0 and progress_bar.n != total_size:
            raise RuntimeError("Could not download file")
        return file_path