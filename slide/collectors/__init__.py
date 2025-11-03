from slide.collectors.scrappers.fileScrapper import LogScrapper, FileScrapper, ConventionalLogScrapper, AgpScrapper
from slide.collectors.scrappers.catalogScrapper import CatalogScrapper
from slide.collectors.webScrapperEngine import WebScrapperEngine
from slide.collectors.downloaders.aria2p import Aria2P



__all__ = [
    "Scrapper",
    "WebScrapper",
    "WebScrapperEngine",
    "LogScrapper",
    "FileScrapper",
    "ConventionalLogScrapper",
    "CatalogScrapper",
    "AgpScrapper",
    "Aria2P",
    "DownloadPolicy",
    "AuthPolicy",
]
