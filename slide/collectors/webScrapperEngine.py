from slide.database.models.download import DownloadDAO
from .base import WebScrapper, Scrapper
from slide.collectors import DownloadPolicy
from slide.logger import Logger

logging = Logger()
logger = logging.get_logger()


class WebScrapperEngine(WebScrapper):
    """
    This engine is responsible for managing the catalog scraping process for all basins available.
    """

    def __init__(
        self, scrappers: list[Scrapper] | Scrapper, dao: DownloadDAO, downloader: DownloadPolicy | None = None
    ) -> None:
        super().__init__(downloader=downloader, scrappers=scrappers)
        self.dao = dao

    def collect(self) -> list:
        """
        Collect data from the catalog engine and return the number of items collected.

        Returns:
            list: The list of collected DTOs.
        """

        logger.info(f"Starting data collection from all scrappers. {len(self.scrappers)} scrappers found.")
        dtos: list = [dto for cs in self.scrappers for dto in cs.scrap()]

        logger.info(f"Collected {len(dtos)} items from all scrappers.")
        logger.info("Inserting collected items into the database.")
        self.dao.bulk_insert(dtos)
        logger.info("Insertion completed.")

        if self.downloader and dtos:
            logger.info(f"Found {len(dtos)} items to download.")
            logger.debug(f"First item: {dtos[0]}")
            self.downloader.download(dtos)

        return dtos
