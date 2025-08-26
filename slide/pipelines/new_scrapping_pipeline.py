from slide.logger import Logger
from slide.pipelines.pipeline import Pipeline
from slide.scrappers.authScrapper import AuthScrapper
from slide.scrappers.catalogEngine import CatalogEngine

logging = Logger()
logger = logging.get_logger()
class NewScrappingPipeline(Pipeline):
    
    def run(self, *args, **kwargs) -> None:
        logger.info("Starting new scraping pipeline...")

        logger.info("Scraping authentication tokens for all basins...")
        authScrapper = AuthScrapper()
        auths = authScrapper.scrap()
        logger.info(f"Found {len(auths)} basins with authentication tokens.")

        logger.info("Starting catalog scraping engine...")
        catalogEngine = CatalogEngine(auths=auths)
        catalogEngine.collect()
        logger.info("Catalog scraping completed.")
