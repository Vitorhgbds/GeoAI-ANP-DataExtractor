"""
create folder structure
verify which files are missing
start scraping
"""


import os
from pathlib import Path
import base64
from typing import Callable

from slide.commons import PATTERN_COMPOSITE_PROFILE, PATTERN_CONVENTIONAL_PROFILE
from slide.crawler.anp import ANPScrapper, ANPSpider
from slide.pipelines.pipeline import Pipeline
from slide.logger import Logger
from slide.providers.download import DownloadProvider

logger = Logger().get_logger()

class ANPScrapingPipeline(Pipeline):
    basins_url = "/anp/TERRESTRE"
    well_url = "/arquivos/public.php/webdav/"
    
    def __init__(self, base_url: str = "https://reate.cprm.gov.br", download_directory: str = "anp_data/", seconds_delay: float = 0.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url: str = base_url
        self.download_directory: os.PathLike = Path(download_directory)
        self.anp_scrapper = ANPScrapper()
        self.seconds_delay = seconds_delay
        self.download_provider = DownloadProvider(base_directory=Path(download_directory))
        
        
    def _generate_authorization_headers(self, basin_links: dict[str, str]) -> dict[str, dict[str,str]]:  
        BASE_HEADER = {
            "Content-Type": "application/xml; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }
        basin_headers = {}
        
        for basin_name, link in basin_links.items():
            user = link.split("/")[-1]
            passcode = "null"
            basic_auth = f"{user}:{passcode}"
            encoded_bytes = base64.b64encode(basic_auth.encode('utf-8'))
            basin_headers[basin_name] = {
                **BASE_HEADER,
                "Authorization" : f"Basic {encoded_bytes.decode('utf-8')}"
                }
            logger.debug(f"Authorization header from basin: {basin_name}")
            logger.debug(f"basic auth: {basic_auth}")
            logger.debug(f"header: {basin_headers[basin_name]}")
        return basin_headers
    
    def _crawl_spiders(self, basin_headers: dict[str, dict[str,str]]) -> dict[str, list[str]]:
        METHOD = "PROPFIND"
        PAYLOAD = """<?xml version="1.0"?>
                    <d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
                    <d:prop>
                        <d:getlastmodified />
                        <d:getetag />
                        <d:getcontenttype />
                        <d:resourcetype />
                        <oc:fileid />
                        <oc:permissions />
                        <oc:size />
                        <d:getcontentlength />
                    </d:prop>
                    </d:propfind>"""
        URL = str(self.base_url + self.well_url)
        
        basin_leafs = {}
        for basin, header in basin_headers.items():
            logger.debug(f"Crawling spider for basin: {basin}")
            logger.debug(f"Start URL: {URL}")
            logger.debug(f"header: {header}")
            
            basin_leafs[basin] = ANPSpider(self.base_url, self.seconds_delay).start_crawl(
                url=URL,
                method=METHOD,
                data=PAYLOAD,
                headers=header,
                use_cache=True,
                cache_path=f".crawl_cache/cache_{basin.replace(" ","_").replace(".","_").replace("-","_")}.json"
            )
        return basin_leafs
    
    def _download(
        self
        ,basin_links: dict[str, list[str]]
        ,basin_headers: dict[str, dict[str,str]]
        ,fetch_dir_name: Callable[[str],os.PathLike] | None = None
        ) -> None:
        
        for basin, links in basin_links.items():
            self.download_provider.download(
                urls=links,
                directory=self.download_directory / basin,
                headers=basin_headers.get(basin),
                fetch_directory_callback=fetch_dir_name,
                use_cache=True,
                cache_path=Path(f".download_cache/cache_{basin.replace(" ","_").replace(".","_").replace("-","_")}.json")
            )
    
    
    def _create_summary(self, basins: list[str]) -> dict[str, int | list[dict[str,int]]]:
        """
        Recursively checks each folder and subfolder from start_path:
        - Verifies if the folder contains files.
        - Checks if a specific subfolder exists.

        :param start_path: The directory to start searching from.
        :param target_folder: The folder name to check existence.
        """
        summary: dict[str, int | list[dict[str,int]]] = {"COMPOSITE": 0, "CONVENTIONAL": 0, "basins_details": []}
        for basin in basins:
            root_folder_name = basin.replace(".","_").replace("-","_").replace(" ","_")
            start_path = self.download_directory / root_folder_name
            basin_summary = {"COMPOSITE": 0, "CONVENTIONAL": 0}
            for root, dirs, files in os.walk(start_path):
                for file in files:
                    file: str = file
                    current_dir: str = Path(root).name
                    profile, pattern = (
                        ("COMPOSITE", PATTERN_COMPOSITE_PROFILE)
                        if file.endswith(".pdf")
                        else ("CONVENTIONAL", PATTERN_CONVENTIONAL_PROFILE)
                    )
                    basin_summary[profile] = (
                        basin_summary[profile] + 1
                        if self.anp_scrapper.matches_patterns(current_dir, [pattern])
                        else basin_summary[profile]
                    )         
            summary["COMPOSITE"] = summary["COMPOSITE"] + basin_summary["COMPOSITE"]
            summary["CONVENTIONAL"] = summary["CONVENTIONAL"] + basin_summary["CONVENTIONAL"]
            logger.info(f"Basin: {basin}")
            logger.info(f"Total composite Profiles: {basin_summary['COMPOSITE']}")
            logger.info(f"Total conventional Profiles: {basin_summary['CONVENTIONAL']}")
        logger.info(f"Total composite profiles: {summary["COMPOSITE"]}")
        logger.info(f"Total conventional profiles: {summary["CONVENTIONAL"]}")
        return summary
        
    def run(self, *args, **kwargs):
        logger.info(":cyclone: Fetching basins entry points...")
        basin_links = self.anp_scrapper.fetch_basin_links(str(self.base_url + self.basins_url))
        logger.debug(f"basin links: {basin_links}")
        logger.info(":white_check_mark: Done.")
        
        logger.info(":cyclone: Generating authorization headers...")
        basin_headers = self._generate_authorization_headers(basin_links)
        logger.debug(f"basin headers: {basin_headers}")
        logger.info(":white_check_mark: Done.")
        
        logger.info(":spider: :spider_web: :web: :cyclone: Starting crawling spiders...")
        basin_catalogs = self._crawl_spiders(basin_headers)
        logger.debug(f"basin catalogs: {basin_catalogs}")
        logger.info(":white_check_mark: Done.")
        
        logger.info(":cyclone: Downloading basins catalogs...")
        self._download(basin_catalogs, basin_headers)
        logger.info(":white_check_mark: Done.")
        
        logger.info(":cyclone: Extracting composite and conventional profile urls from catalogs...")
        #basin_profiles = self._download_leafs(basin_catalogs, basin_headers)
        logger.info(":white_check_mark: Done.")
        
        logger.info(":cyclone: Downloading composite and conventional profiles from urls...")
        #self._download(basin_profiles, basin_headers, self.anp_scrapper.fetch_profile_path)
        logger.info(":white_check_mark: Done.")
        
        logger.info(":cyclone: Summarizing...")
        #self._create_summary(basin_headers.keys())
        logger.info(":white_check_mark: Done.")