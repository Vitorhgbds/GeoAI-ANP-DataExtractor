import asyncio
import json
import os
import pathlib
import re
from time import sleep
import requests
from bs4 import BeautifulSoup, element
from slide.commons import BAR_FORMAT, PATTERNS
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
        normalized_text = re.sub(r"[%20_-]+", " ", text).strip()
        matches = [bool(re.search(pattern, normalized_text, re.IGNORECASE)) for pattern in patterns]
        return True in matches
    
    def fetch_profile_path(self, file_url: str, *args, **kwargs) -> os.PathLike:
        # Splitting the url to get the path
        directory_tree = file_url.split("/POCO/")[-1].split("/")
        # Removing file name
        path = "/".join(directory_tree[:-1])
        return pathlib.Path(path)
    
        
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
    
    def download_from_leaf(self, base_url: str, leafs: list[str], basin: str, directory: str = "./data", *args, **kwargs) -> None:
        logger.info(f"Trying to download leafs from basin: {basin}")
        if not leafs:
            logger.debug("No leafs to download.")
            return
        METHOD = kwargs.get("method", "PROPFIND")
        HEADERS = kwargs.get("headers", {})
        PAYLOAD = kwargs.get("data")
        BASIN_NAME = basin.lower().replace(" ","_").replace("-","_").replace(".","_")
        
        cache = CacheProvider(
            pathlib.Path(kwargs.get("cache_path", "cache_download.json"))
        )
        use_cache = kwargs.get("use_cache", False)
        
        downloaded_leafs = []
        if use_cache:
            logger.debug(f"Loading leafs from cache.")
            content = cache.fetch()
            downloaded_leafs = content.get("downloaded_leafs", [])
        else:
            cache.clean()
            
        leafs_to_download = set(leafs).difference(set(downloaded_leafs))
        
        overall_progress = self.progress_provider.get_progress(ProgressType.OVERALL)
        overall_task = overall_progress.add_task('', total=len(leafs_to_download))
        live = self.progress_provider.get_live()
        i = 0
        with live:
            for url in leafs_to_download:
                overall_progress.update(overall_task, description='[bold #AAAAAA](%d out of %d leafs downloaded)' % (i, len(leafs_to_download)))
                if url in downloaded_leafs:
                    i += 1
                    continue
                
                response = requests.request(METHOD, url, headers=HEADERS, data=PAYLOAD)
                links = self.fetch_links(response.text, "xml")
                filtered_links = [link for link in links if link.lower().endswith(('.pdf', '.dlis'))]

                if len(filtered_links) < len(links) - 1:
                    logger.debug(f"Files removed before download.")
                    logger.debug(f"{set(links).difference(set(filtered_links))}")
                    logger.debug(f"Files to download: {filtered_links}")
                    
                retries = 0
                max_retries = 10
                while retries < max_retries:
                    try:
                        download_files_concurrently(
                            filtered_links=filtered_links,
                            base_url=base_url,
                            directory=directory,
                            basin_name=BASIN_NAME,
                            headers=HEADERS,
                            data=PAYLOAD)
                        downloaded_leafs.append(url)
                        retries = max_retries
                        i += 1
                        overall_progress.update(overall_task, advance=1)
                    except Exception as e:
                        logger.exception(e)
                        retries += 1
                        logger.warning(f"Failed to download files retrying: {retries}")
                    finally:
                        cache.save({"downloaded_leafs":downloaded_leafs})
            #overall_progress.update(overall_task, description="[bold green]%s leafs download, done!" % len(leafs_to_download))
            overall_progress.stop_task(overall_task)
            overall_progress.update(overall_task, visible=False)

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
        leaf = [link for link in links if self.scrapper.matches_patterns(link.split("/")[-1], PATTERNS)]
        next = [link for link in links[1:] if link.endswith("/")] if len(links) > 1 and not leaf else []
        return next, leaf
        
        
