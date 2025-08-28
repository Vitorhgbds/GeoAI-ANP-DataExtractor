from pathlib import Path
from slide.database.models.download import DownloadDAO
from slide.downloaders.aria2p import Aria2P
from slide.logger import Logger
from slide.pipelines.pipeline import Pipeline
from slide.scrappers import Scrapper
from slide.scrappers.authScrapper import AuthScrapper
from slide.scrappers.engine import Engine
from slide.scrappers.catalogScrapper import CatalogScrapper
from slide.scrappers.fileScrapper import AgpScrapper, LogScrapper

logging = Logger()
logger = logging.get_logger()
class ScrappingPipeline(Pipeline):

    def __init__(self, out_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_dir = Path(out_dir)

    def run(self, *args, **kwargs) -> None:
        logger.info("Starting new scraping pipeline...")

        logger.info("Fetching existing catalog downloads...")
        dao = DownloadDAO(self.out_dir / "download.db")
        catalogs = dao.fetch_where(f"lower(name) LIKE '%md5%.txt'")
        catalog_map = {catalog.basin: f"{catalog.path}/{catalog.name}" for catalog in catalogs}
        logger.info(f"Found {len(catalogs)} existing catalog downloads.")

        logger.info("Scraping authentication tokens for all basins...")
        authScrapper = AuthScrapper()
        auths = authScrapper.scrap()
        logger.info(f"Found {len(auths)} basins with authentication tokens.")

        logger.info("Starting catalog scrappers for all basins...")
        fuel: list[Scrapper] = []
        for auth in auths:
            logger.debug(f" - {auth[0]}: {auth[1]}")
            if auth[0] in catalog_map and Path(catalog_map[auth[0]]).exists():
                logger.debug(f"   -> Catalog already exists at {catalog_map[auth[0]]}, skipping...")
                continue
            else:
                fuel.append(CatalogScrapper(auth, self.out_dir / auth[0], use_cache=True))
        logger.info(f"Initialized {len(fuel)} catalog scrappers.")

        logger.info("Starting catalog scraping engine...")
        if fuel:
            engine = Engine(scrappers=fuel, downloader=Aria2P(cache_dao=dao))
            catalogs = engine.collect()
        logger.info("Catalog scraping completed.")

        logger.info("Fetching completed catalog downloads...")
        catalogs = dao.fetch_where(f"lower(name) LIKE '%md5%.txt'")
        logger.info(f"Found {len(catalogs)} catalog downloads.")

        logger.info("Starting agp scrappers for all catalogs...")
        fuel = [AgpScrapper(catalog) for catalog in catalogs if (Path(catalog.path) / catalog.name).exists()]
        engine = Engine(scrappers=fuel, downloader=Aria2P(cache_dao=dao))
        engine.collect()
        logger.info("Agp scraping completed.")