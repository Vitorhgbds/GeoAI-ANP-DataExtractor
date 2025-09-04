from slide.downloaders import DownloadPolicy
from slide.logger import Logger
from slide.scrappers import Scrapper, WebScrapperEngine
from tqdm import tqdm

logging = Logger()
logger = logging.get_logger()
class Engine(WebScrapperEngine):
    """
    This engine is responsible for managing the catalog scraping process for all basins available.
    """

    def __init__(self, scrappers: list[Scrapper] | Scrapper, downloader: DownloadPolicy | None = None) -> None:
        super().__init__(downloader=downloader, scrappers=scrappers)

    def collect(self) -> list:
        """
        Collect data from the catalog engine and return the number of items collected.

        Returns:
            int: The number of items collected.
        """
        dtos: list = [
            dto
            for cs in tqdm(self.scrappers, desc="Total scrappers")
            for dto in cs.scrap()
        ]
        if self.downloader and dtos:
            logger.info(f"Found {len(dtos)} items to download.")
            logger.debug(f"First item: {dtos[0]}")
            self.downloader.download(dtos)

        return dtos