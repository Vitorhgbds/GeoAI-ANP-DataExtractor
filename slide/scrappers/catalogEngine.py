

from pathlib import Path
from slide.database.models.download import DownloadDAO, DownloadDTO, DownloadStatus
from slide.providers.cache import CacheProvider
from slide.scrappers import WebScrapperEngine
from slide.scrappers.catalogScrapper import CatalogScrapper
from slide.downloaders.aria2p import Aria2P


class CatalogEngine(WebScrapperEngine):
    """
    Scraper for the catalog engine.
    """

    def __init__(self, auths: dict[str,str]) -> None:
        self.dao = DownloadDAO(db_path=Path("./download.db"))
        self.downloader = Aria2P(cache_dao=self.dao)
        self.auths = auths
        self.download_directory = Path("./downloads")

    def collect(self) -> int:
        """
        Collect data from the catalog engine and return the number of items collected.

        Returns:
            int: The number of items collected.
        """
        downloads = []

        for name, auth in self.auths.items():
            header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/xml; charset=UTF-8",
            "Authorization": auth
            }
            cache = CacheProvider(self.download_directory / f"catalog-cache-{name}.json")
            scrapper = CatalogScrapper(header=header, delay=1, cache=cache, use_cache=True)
            links = scrapper.scrap()
            downloads.extend([
                DownloadDTO(
                url=url,
                basin=name,
                name=url.split("/")[-1],
                path=str(self.download_directory / name), # type: ignore
                status=DownloadStatus.WAITING,
                headers=header
                ) for url in links
            ])

        self.downloader.download(downloads)

        return len(downloads)