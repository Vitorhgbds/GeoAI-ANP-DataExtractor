import asyncio
import json
import os
import pathlib
import re
from time import sleep
import requests
from bs4 import BeautifulSoup, element
from slide.commons import (BAR_FORMAT, PATTERNS, PATTERN_PROFILES, PATTERN_MD5_CATALOG, PATTERN_COMPOSITE_PROFILE, PATTERN_CONVENTIONAL_PROFILE)
from slide.crawler.scrapper import Scrapper
from slide.crawler.spider import Spider
from slide.crawler.download import download_files_concurrently
from slide.logger import Logger

from slide.providers import CacheProvider, ProgressProvider, ProgressType

logger = Logger().get_logger()
class ANPScrapper(Scrapper):
    
    def __init__(self, *args, **kwargs):
        self.progress_provider = ProgressProvider()
        
    def matches_patterns(self, text: str, patterns: list[str]) -> bool:
        normalized_text = text.strip()
        matches = [bool(re.search(pattern, normalized_text)) for pattern in patterns]
        return True in matches
    
    def fetch_profile_path(self, file_url: str, *args, **kwargs) -> os.PathLike:
        # Splitting the url to get the path
        directory_tree = file_url.split("/POCO/")[-1].split("/")
        path = "/".join(directory_tree[0:])
        return pathlib.Path(path)
    
    def fetch_profile_links(self, catalog_path: pathlib.Path, *args, **kwargs) -> dict[str, list[str]]:
        profile_links = {}
        # read each line of a file and find a link in line
        with open(catalog_path, "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                link = line.split("..")[-1].strip()
                if self.matches_patterns(link, [PATTERN_CONVENTIONAL_PROFILE]):
                    profile_links["conventional"] = profile_links.get("conventional", []) + [link.replace(" ", "%20")]
                elif self.matches_patterns(link, [PATTERN_COMPOSITE_PROFILE]):
                    profile_links["composite"] = profile_links.get("composite", []) + [link.replace(" ", "%20")]
        return profile_links
    
    def fetch_basin_links(self, url: str, *args, **kwargs) -> dict[str, str]:
        response = requests.get(url)
        
        if response.status_code != 200:
            raise requests.exceptions.RequestException(
                f"Failed to fetch basin links from {url} with status code {response.status_code}"
                )

        basin_link = {}
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find all <h4> tags that start with 'Bacia'
        titles: list[element.Tag] = soup.find_all('h4')
        for title in titles:
            
            basin_name: str = title.get_text(strip=True).lower()
            if not basin_name.startswith('bacia'):
                continue
            
            # Find the nearest <a> tag with an href attribute
            link_tag = title.find_next('a', href=True)
            if not link_tag:
                continue
            
            link = link_tag['href']
            # Store the basin name and link in the dictionary
            basin_link[basin_name] = link
            
        return basin_link
    

class ANPSpider(Spider):
    def __init__(self, base_url: str, seconds_delay: float = 0.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url: str = base_url  
        self.scrapper: ANPScrapper = ANPScrapper()
        self.seconds_delay = seconds_delay
        logger.info(f"Ban prevention delay set to {seconds_delay} seconds")
        
    def search(
        self, 
        url: str, 
        data: str,
        method: str = "PROPFIND", 
        *args, **kwargs
    ) -> tuple[list[str], list[str]]:
        logger.debug(f"Searching URL: {url}")
        sleep(self.seconds_delay)
        response = requests.request(method, url, headers=self.headers, data=data)
        links = [str(self.base_url + link) for link in self.scrapper.fetch_links(response.text, "xml")]
        leaf = [link for link in links if self.scrapper.matches_patterns(link.split("/")[-1], [PATTERN_MD5_CATALOG])]
        next = [link for link in links[1:] if link.endswith("/")] if len(links) > 1 and not leaf else []
        return next, leaf
        
        
