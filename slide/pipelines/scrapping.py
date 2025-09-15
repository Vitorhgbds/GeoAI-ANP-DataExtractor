from pathlib import Path

from tqdm import tqdm
from slide.database.models.agp import AgpLithologyDAO, AgpSummaryDAO
from slide.database.models.download import AGPDownloadDAO, CatalogDownloadDAO, DownloadDAO, LogDownloadDAO
from slide.downloaders.aria2p import Aria2P
from slide.logger import Logger
from slide.pipelines import Pipeline
from slide.scrappers import Scrapper
from slide.scrappers.agpScrapper import Lithology, Summary
from slide.scrappers.authScrapper import AuthScrapper
from slide.scrappers.engine import Engine
from slide.scrappers.catalogScrapper import CatalogScrapper
from slide.scrappers.downloadScrapper import AgpScrapper, ConventionalLogScrapper, LogScrapper

logging = Logger()
logger = logging.get_logger()
class ScrappingPipeline(Pipeline):

    def __init__(self, out_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_dir = Path(out_dir)

    def run(self, *args, **kwargs) -> None:
        logger.info("Starting new scraping pipeline...")

        logger.info("Fetching existing catalog downloads...")
        dao = CatalogDownloadDAO(self.out_dir / "download.db")
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
            basin, token = auth
            logger.debug(f" Basin and token {basin}: {token}")
            if basin in catalog_map and Path(catalog_map[basin]).exists():
                logger.debug(f"   -> Catalog already exists at {catalog_map[basin]}, skipping...")
                continue
            else:
                fuel.append(CatalogScrapper(auth, self.out_dir / basin, use_cache=True))
        logger.info(f"Initialized {len(fuel)} catalog scrappers.")

        logger.info("Starting catalog scraping engine...")
        if fuel:
            engine = Engine(scrappers=fuel, downloader=Aria2P(cache_dao=dao))
            catalogs = engine.collect()
        logger.info("Catalog scraping completed.")

        logger.info("Fetching completed catalog downloads...")
        catalogs = dao.fetch_where(f"lower(name) LIKE '%md5%.txt'")
        logger.info(f"Found {len(catalogs)} catalog downloads.")

        logger.info("Starting log scrappers for all catalogs...")
        fuel = [ConventionalLogScrapper(catalog) for catalog in catalogs if (Path(catalog.path) / catalog.name).exists()]
        engine = Engine(scrappers=fuel)
        files = engine.collect()
        logger.info("Log scraping completed.")
        logger.info(f"Found {len(files)} log files to process.")
        dao = LogDownloadDAO(self.out_dir / "download.db")
        dao.bulk_insert(files)

        logger.info("Starting agp scrappers for all catalogs...")
        dao = AGPDownloadDAO(self.out_dir / "download.db")
        fuel = [AgpScrapper(catalog) for catalog in catalogs if (Path(catalog.path) / catalog.name).exists()]
        engine = Engine(scrappers=fuel, downloader=Aria2P(overwrite=False, cache_dao=dao))
        files = engine.collect()
        logger.info("AGP scraping completed.")
        logger.info(f"Found {len(files)} AGP files to process.")

        logger.info("Starting agp scrappers for all catalogs...")
        fuel = [AgpScrapper(catalog) for catalog in catalogs if (Path(catalog.path) / catalog.name).exists()]
        engine = Engine(scrappers=fuel, downloader=Aria2P(overwrite=False, cache_dao=dao))
        files = engine.collect()
        logger.info("Agp scraping completed.")

        logger.info("Starting agp summary scrappers for all agp files...")
        files = dao.fetch_where(f"lower(path) LIKE '%agp%' or lower(name) LIKE '%agp%.txt'")
        logger.info(f"Found {len(files)} agp files to process.")
        fuel = [Summary(Path(agp.path) / agp.name) for agp in tqdm(files, desc="Total agp Scrappers to initialize") if (Path(agp.path) / agp.name).exists()]
        engine = Engine(scrappers=fuel)
        summaries_dto = engine.collect()
        logger.info(f"Found {len(summaries_dto)} agp files with summary to process.")
        summaries_dao = AgpSummaryDAO(self.out_dir / "download.db")
        summaries_dao.bulk_insert(summaries_dto)
        summaries_dao.close()
        logger.info("Agp summary scraping completed and added to database.")

        logger.info("Starting lithology scrappers for all agp files...")
        logger.info(f"Found {len(files)} agp files to process.")
        fuel = [Lithology(Path(agp.path) / agp.name) for agp in tqdm(files, desc="Total agp Scrappers to initialize") if (Path(agp.path) / agp.name).exists()]
        engine = Engine(scrappers=fuel)
        lithologies_dto = engine.collect()
        lithologies_dao = AgpLithologyDAO(self.out_dir / "download.db")
        logger.info(f"Found {len(lithologies_dto)} agp files with lithology entries to process.")
        lithologies_dao.bulk_insert(lithologies_dto)
        lithologies_dao.close()
        logger.info("Lithology scraping completed and added to database.")