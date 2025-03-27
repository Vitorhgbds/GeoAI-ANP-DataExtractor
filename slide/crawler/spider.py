from abc import abstractmethod, ABC
from pathlib import Path
import requests
import json
from tqdm.auto import tqdm

from slide.crawler.scrapper import Scrapper
from slide.logger import Logger
from slide.providers.cache import CacheProvider

logger = Logger().get_logger() 

class Spider(ABC):
    
    def __init__(self, 
                 headers: dict[str, str] = {},
                 user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                 *args, **kwargs):
        
        self.user_agent = user_agent
        self.set_headers(headers)
        self.scrapper: Scrapper = Scrapper()
        
    
    def set_headers(self, headers: dict) -> None:
        self.headers = headers
        if not headers.get("User-Agent"):
            self.headers["User-Agent"] = self.user_agent
            
    @abstractmethod
    def search(
        self,
        url: str, 
        *args, **kwargs
    ) -> tuple[list[str], list[str]]:
        """search method should be implemented by the child class to extract links from the provided url.
        NOTE: This method can be used to extract whatever information is needed from the url.

        Args:
            url (str): The URL to fetch the response from.
        Returns:
            list[str]: A list of next links to crawl.
            list[str]: A list contents that match the search criteria.
        """
        METHOD = kwargs.get("method", "GET")
        PAYLOAD = kwargs.get("data")
        
        response = requests.request(METHOD, url, headers=self.headers, data=PAYLOAD)
        if response.status_code != 200:
            raise requests.RequestException(
                f"Error on request"
                f"url: {url}"
                f"status code: {response.status_code}"
                f"method: {METHOD}"
                f"data: {PAYLOAD}"
            )
        links = self.scrapper.fetch_links(response.content, "html")
        leaf = [] if links else [url]
        next = [] if leaf else links 
        return next, leaf   
    
    
    def start_crawl(
        self, 
        url: str,
        *args, **kwargs
        ) -> list[str]:
        cache = CacheProvider(
            Path(kwargs.get("cache_path", "cache.json"))
        )
        use_cache = kwargs.get("use_cache", False)
        
        headers = kwargs.get("headers", {})
        if headers:
            self.set_headers(headers)
        
        urls = [url]
        results = []
        
        if use_cache:
            content = cache.fetch()
            urls = content.get("urls", [url])
            results = content.get("results", [])
        else:
            cache.clean()
        
        logger.debug(f"total urls for crawling: {len(urls)}")
        n = len(urls)
        max_retries = 10
        retries = 0
        pbar = tqdm(desc="Depth exploring links", total=n)
        while retries < max_retries:
            try:
                while urls:
                    current = urls[0]
                    next, result = self.search(current, **kwargs)
                    urls.pop(0)
                    urls.extend(next)
                    results.extend(result)
                    n += len(next)
                    pbar.total = n
                    pbar.refresh()
                    pbar.update(1)
                retries = max_retries
            except Exception as e:
                logger.error(e)
                logger.info(f"Retrying number: {retries} of maximum {max_retries}")
                retries = retries + 1
                continue
            finally:
                cache.save({"urls":urls, "results":results})
        return results