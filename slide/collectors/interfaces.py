from abc import ABC, abstractmethod
from slide.collectors.downloaders.downloadPolicy import DownloadPolicy
from slide.database.models.download import DownloadDTO

class DownloadPolicy(ABC):
    @abstractmethod
    def download(self, dtos: list[DownloadDTO]) -> list[str]:
        """
        Download files based on the provided DTOs.

        Args:
            dtos (list[DownloadDTO]): The list of download DTOs to process.

        Returns:
            bool: True if the download was successful, False otherwise.
        """
        pass


class AuthPolicy(ABC):
    @abstractmethod
    def get(self) -> list:
        pass
    

class Scrapper(ABC):
    @abstractmethod
    def scrap(self) -> list:
        """
        Scrape and return a list of scrapped contents.

        Returns:
            list: The list of scraped contents.
        """
        pass


class WebScrapper(ABC):
    """
    Abstract class for web scrapers.
    """

    def __init__(self, downloader: DownloadPolicy, scrappers: list[Scrapper] | Scrapper) -> None:
        self.downloader = downloader
        self.scrappers = scrappers if isinstance(scrappers, list) else [scrappers]

    @abstractmethod
    def collect(self) -> list:
        """
        Collect data from the web and return the number of items collected.

        Returns:
            list: The list of items collected.
        """
        pass
