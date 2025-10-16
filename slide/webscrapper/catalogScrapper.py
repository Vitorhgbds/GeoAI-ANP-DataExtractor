import json
from pathlib import Path
import re
from time import sleep
from bs4 import BeautifulSoup
import requests
from slide.commons import BASE_URL, WELL_URL
from slide.database.models.download import CatalogDownloadDTO, DownloadStatus
from slide.logger import Logger
from slide.providers.cache import CacheProvider
from . import Scrapper
from slide.webscrapper.authPolicy import ANPAuthPolicy

logging = Logger()
logger = logging.get_logger()


class CatalogScrapper(Scrapper):
    def __init__(self, out_dir: Path, use_cache: bool = False, delay: int = 0) -> None:
        super().__init__()
        self.authPolicy = ANPAuthPolicy()
        self.headers = {
            "host": "reate.cprm.gov.br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/xml; charset=UTF-8",
        }
        self.out_dir = out_dir
        self.cache = CacheProvider(Path(out_dir) / "catalog-cache.json")
        self.use_cache = use_cache
        self.start_url = BASE_URL + WELL_URL
        self.delay = delay
        self.results: list[str] = []

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
        PARSER = "lxml-xml"
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
        links = [str(BASE_URL + href) for href in hrefs]

        leaf = [link for link in links if self.isCatalogFile(link.split("/")[-1])]
        next = [link for link in links[1:] if link.endswith("/")] if len(links) > 1 and not leaf else []
        return next, leaf

    def deep_search(self) -> list[str]:
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

    def scrap(self) -> list[CatalogDownloadDTO]:
        # Implement the scraping logic here

        if self.use_cache:
            content = self.cache.fetch()
            self.urls = content.get("urls", [self.start_url])
            self.results = content.get("results", [])
        else:
            self.cache.clean()

        catalogs: list[CatalogDownloadDTO] = []
        self.auths = self.authPolicy.get()
        for basin, token in self.auths:
            self.headers["Authorization"] = token
            self.urls = [self.start_url]
            self.results = []

            max_retries = 10
            retries = 0
            while retries < max_retries:
                try:
                    logger.debug("Starting deep search...")
                    self.deep_search()
                    logger.debug(f"Deep search completed. Found {len(self.results)} results.")
                    break
                except Exception as e:
                    logger.error(f"Error occurred: {e}")
                    retries = retries + 1
                    logger.debug(f"Retrying {retries}/{max_retries}...")
                    continue
                finally:
                    self.cache.save({"urls": self.urls, "results": self.results})
            catalogs.extend(
                [
                    CatalogDownloadDTO(
                        url=url,
                        basin=basin,
                        name=url.split("/")[-1],
                        path=str(f"{self.out_dir}/{basin}"),
                        status=DownloadStatus.WAITING.value,
                        headers=json.dumps(self.headers),
                    )
                    for url in self.results
                ]
            )

        return catalogs
