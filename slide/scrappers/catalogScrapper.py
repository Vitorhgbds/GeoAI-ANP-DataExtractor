import re
from time import sleep
from bs4 import BeautifulSoup
import requests
from slide.providers.cache import CacheProvider
from slide.scrappers import Scrapper


class CatalogScrapper(Scrapper):

    def __init__(self, header: dict[str,str], cache: CacheProvider, use_cache: bool = False, delay: int = 0) -> None:
        super().__init__()
        self.delay = delay
        self.base_url = "https://reate.cprm.gov.br"
        self.start_url = self.base_url + "/arquivos/public.php/webdav/"
        self.headers = header
        self.cache = cache
        self.use_cache = use_cache
        self.urls = [self.start_url]
        self.results = []


    def isCatalogFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)^md5.*\.txt$", name.strip()))
    

    def fetch(self, url: str) -> tuple[list[str], list]:
        """find and extract links from the provided url.
        NOTE: This method can be used to extract whatever information is needed from the url.

        Args:
            url (str): The URL to fetch the response from.
        Returns:
            list[str]: A list of next links to search.
            list: A list contents that match the search criteria.
        """
        PARSER = "XML"
        METHOD = "PROPFIND"
        PAYLOAD = """<?xml version="1.0"?>
                    <d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
                    <d:prop>
                        <d:getlastmodified />
                        <d:getetag />
                        <d:getcontenttype />
                        <d:resourcetype />
                        <oc:fileid />
                        <oc:permissions />
                        <oc:size />
                        <d:getcontentlength />
                    </d:prop>
                    </d:propfind>"""
        SEARCH_TAG = "href"

        sleep(self.delay)
        response = requests.request(METHOD, url, headers=self.headers, data=PAYLOAD)

        soup = BeautifulSoup(response.content, PARSER)
        hrefs = [href.text.strip() for href in soup.find_all(SEARCH_TAG)]
        links = [str(self.base_url + href) for href in hrefs]

        leaf = [link for link in links if self.isCatalogFile(link.split("/")[-1])]
        next = [link for link in links[1:] if link.endswith("/")] if len(links) > 1 and not leaf else []
        return next, leaf


    def deep_search(self, urls: list[str], results: list[str]) -> list[str]:
        """Perform a deep search on the provided URL.

        Args:
            url (str): The URL to perform the deep search on.

        Returns:
            list[str]: A list of results from the deep search.
        """
    
        while self.urls:
            current = self.urls[0]
            next, result = self.fetch(current)
            self.urls.pop(0)
            self.urls.extend(next)
            self.results.extend(result)
        return self.results
    

    def scrap(self) -> list[str]:
        # Implement the scraping logic here

        if self.use_cache:
            content = self.cache.fetch()
            self.urls = content.get("urls", [self.start_url])
            self.results = content.get("results", [])
        else:
            self.cache.clean()

        max_retries = 10
        retries = 0

        while retries < max_retries:
            try:
                self.deep_search(self.urls, self.results)
                break
            except Exception as e:
                print(f"Error occurred: {e}")
                retries = retries + 1
                continue
            finally:
                self.cache.save({"urls": self.urls, "results": self.results})

        return self.results