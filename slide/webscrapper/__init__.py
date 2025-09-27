from slide.webscrapper.base import Scrapper, WebScrapper
from slide.webscrapper.fileScrapper import LogScrapper, FileScrapper, ConventionalLogScrapper, AgpScrapper
from slide.webscrapper.catalogScrapper import CatalogScrapper
from slide.webscrapper.webScrapperEngine import WebScrapperEngine





__all__ = ["Scrapper", 
           "WebScrapper",
           "WebScrapperEngine",
           "LogScrapper", 
           "FileScrapper", 
           "ConventionalLogScrapper", 
           "CatalogScrapper", 
           "AgpScrapper"]