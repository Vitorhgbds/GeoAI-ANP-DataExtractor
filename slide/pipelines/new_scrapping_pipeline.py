from slide.database.models.download import DownloadDAO
from slide.downloaders.aria2p import Aria2P
from slide.logger import Logger
from slide.pipelines.pipeline import Pipeline
from slide.scrappers.authScrapper import AuthScrapper
from slide.scrappers.catalogEngine import CatalogEngine, Engine
from slide.scrappers.catalogScrapper import CatalogScrapper
from slide.scrappers.fileScrapper import LogScrapper

logging = Logger()
logger = logging.get_logger()
class NewScrappingPipeline(Pipeline):
    
    def run(self, *args, **kwargs) -> None:
        logger.info("Starting new scraping pipeline...")

        logger.info("Scraping authentication tokens for all basins...")
        authScrapper = AuthScrapper()
        auths = authScrapper.scrap()
        logger.info(f"Found {len(auths)} basins with authentication tokens.")

        fuel = []
        for auth in auths:
            logger.info(f" - {auth[0]}: {auth[1]}")
            fuel.append(CatalogScrapper(auth, "./downloads/" + auth[0]))

        logger.info("Starting catalog scraping engine...")
        dao = DownloadDAO("./downloads/download.db")
        catalogEngine = Engine(catalogScrapper=fuel, downloader=Aria2P(dao))
        catalogs = catalogEngine.collect()
        logger.info("Catalog scraping completed.")



        logger.info(f" - {catalog.name}: {catalog.url}")
        fuel = []
        for catalog in catalogs:
            fuel.append(LogScrapper(catalog))
