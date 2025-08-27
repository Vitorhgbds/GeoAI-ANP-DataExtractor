from slide.database.models.download import DownloadDTO
from slide.downloaders import DownloadPolicy
from slide.logger import Logger
from slide.scrappers import WebScrapperEngine
from slide.scrappers.catalogScrapper import CatalogScrapper

logging = Logger()
logger = logging.get_logger()
class Engine(WebScrapperEngine):
    """
    This engine is responsible for managing the catalog scraping process for all basins available.
    """

    def __init__(self, catalogScrapper: CatalogScrapper, downloader: DownloadPolicy) -> None:
        super().__init__(downloader=downloader, scrappers=catalogScrapper)

    def collect(self) -> list[DownloadDTO]:
        """
        Collect data from the catalog engine and return the number of items collected.

        Returns:
            int: The number of items collected.
        """
        catalogs: list[DownloadDTO] = [
            catalog 
            for cs in self.scrappers 
            for catalog in cs.scrap()
        ]
        self.downloader.download(catalogs)

        return catalogs