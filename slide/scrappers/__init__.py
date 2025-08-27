from abc import ABC, abstractmethod
from slide.downloaders import DownloadPolicy


class Scrapper(ABC):

    @abstractmethod
    def scrap(self) -> list:
        """
        Scrape and return a list of scrapped contents.

        Returns:
            list: The list of scraped contents.
        """
        pass


class WebScrapperEngine(ABC):
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