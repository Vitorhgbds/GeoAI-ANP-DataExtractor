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