

from pathlib import Path
from typing import Tuple
from slide.database.models.download import DownloadDAO, DownloadDTO, DownloadStatus
from slide.logger import Logger
from slide.providers.cache import CacheProvider
from slide.scrappers import WebScrapperEngine
from slide.scrappers.catalogScrapper import CatalogScrapper
from slide.downloaders.aria2p import Aria2P

logging = Logger()
logger = logging.get_logger()
class CatalogEngine(WebScrapperEngine):
    """
    This engine is responsible for managing the catalog scraping process for all basins available.
    """

    def __init__(self, auths: list[Tuple[str,str]]) -> None:
        self.download_directory = Path("./downloads")
        self.downloads = DownloadDAO(db_path=Path("./downloads/download.db"))
        self.downloader = Aria2P(cache_dao=self.downloads)
        self.auths = auths

    def collect(self) -> int:
        """
        Collect data from the catalog engine and return the number of items collected.

        Returns:
            int: The number of items collected.
        """
        files: list[DownloadDTO] = []

        for name, auth in self.auths:
            header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/xml; charset=UTF-8",
            "Authorization": auth
            }
            logger.debug(f"Scraping catalog for basin: {name}")
            cache = CacheProvider(self.download_directory / name / f"catalog-cache.json")
            scrapper = CatalogScrapper(header=header, delay=0, cache=cache, use_cache=True)
            links = scrapper.scrap()
            files.extend([
                DownloadDTO(
                url=url,
                basin=name,
                name=url.split("/")[-1],
                path=str(self.download_directory / name),
                status=DownloadStatus.WAITING,
                headers=header
                ) for url in links
            ])

        self.downloads.bulk_insert(files)
        dtos = self.downloads.fetch_where(f"lower(name) LIKE '%md5%.txt' and status = '{DownloadStatus.WAITING.value}'")
        self.downloader.download(dtos)

        return len(files)