from slide.collectors.base import Scrapper, WebScrapper
from slide.collectors.fileScrapper import LogScrapper, FileScrapper, ConventionalLogScrapper, AgpScrapper
from slide.collectors.catalogScrapper import CatalogScrapper
from slide.collectors.webScrapperEngine import WebScrapperEngine
from slide.collectors.downloaders.aria2p import Aria2P
from slide.collectors.downloaders.downloadPolicy import DownloadPolicy


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
]
