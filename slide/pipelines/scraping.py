"""
create folder structure
verify which files are missing
start scraping
"""


import json
import os
from pathlib import Path
import base64
from typing import Callable
import re

from slide.commons import PATTERN_COMPOSITE_PROFILE, PATTERN_CONVENTIONAL_PROFILE
from slide.crawler.anp import ANPScrapper, ANPSpider
from slide.database.models.download import DownloadDAO, DownloadDTO, DownloadStatus
from slide.downloaders.aria2p import Aria2P
from slide.pipelines.pipeline import Pipeline
from slide.logger import Logger
from slide.providers.cache import CacheProvider

logger = Logger().get_logger()

class ANPScrapingPipeline(Pipeline):
    basins_url = "/anp/TERRESTRE"
    well_url = "/arquivos/public.php/webdav/"
    
    def __init__(self, base_url: str = "https://reate.cprm.gov.br", download_directory: str = "anp_data/", seconds_delay: float = 0.0, use_cache: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url: str = base_url
        self.download_directory: os.PathLike = Path(download_directory)
        self.anp_scrapper = ANPScrapper()
        self.seconds_delay = seconds_delay
        self.use_cache = use_cache
        self.dao = DownloadDAO(db_path=Path("./downloads/download.db"))
        if not self.use_cache:
            self.dao.clean()
        self.downloader = Aria2P(cache_dao=self.dao)
        
    def _generate_authorization_headers(self, basin_links: dict[str, str]) -> dict[str, dict[str,str]]:  
        BASE_HEADER = {
            "host": "reate.cprm.gov.br", 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
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
        dtos = []
        for basin, header in basin_headers.items():
            logger.debug(f"Crawling spider for basin: {basin}")
            logger.debug(f"Start URL: {URL}")
            logger.debug(f"header: {header}")
            header["X-Requested-With"] = "XMLHttpRequest"
            header["Content-Type"] = "application/xml; charset=UTF-8"
            
            basin_leafs[basin] = ANPSpider(self.base_url, self.seconds_delay).start_crawl(
                url=URL,
                method=METHOD,
                data=PAYLOAD,
                headers=header,
                use_cache=True,
                cache_path=f'.crawl_cache/cache_{basin.replace(" ","_").replace(".","_").replace("-","_")}.json'
            )
            dtos.extend([DownloadDTO(
                url=leaf,
                basin=basin,
                name=leaf.split("/")[-1],
                path=str(self.download_directory / basin), # type: ignore
                status=DownloadStatus.WAITING,
                headers=header
            ) for leaf in basin_leafs[basin]])
        logger.info(f"Found {len(dtos)} leafs in {len(basin_leafs)} basins.")
        self.dao.bulk_insert(dtos)
        
        return basin_leafs
    
    def _download(
        self
        ,dtos: list[DownloadDTO]
        ) -> dict[str, list[Path]]:
        
        BASE_DOWNLOAD_HEADER = {
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        }
        basin_files = {}
        downloader = Aria2P()
        return basin_files
    
    def _fetch_profiles_links(self, dtos: list[DownloadDTO]) -> dict[str, list[str]]:
        profiles_links = {}
        new_dtos = []
        for dto in dtos:
            
            catalog_path = Path(dto.path) / dto.name
            basin = dto.basin
            if not catalog_path.exists():
                logger.warning(f"Catalog path does not exist: {catalog_path}")
                continue
            
            if basin not in profiles_links:
                profiles_links[basin] = []
            
            links = self.anp_scrapper.fetch_profile_links(catalog_path=catalog_path)
            all_links = links.get("composite", []) + links.get("conventional", [])
            all_links_normalized = ["/".join(link.split("/")[2:]) for link in all_links]
            profiles_links[basin].extend([str(self.base_url + self.well_url + link) for link in all_links_normalized])
            
            new_dtos.extend([DownloadDTO(
                url=link,
                basin=basin,
                name=link.split("/")[-1],
                path=str(self.download_directory / basin / self.anp_scrapper.fetch_profile_path(link)), # type: ignore
                status=DownloadStatus.WAITING,
                headers=dto.headers
            ) for link in profiles_links[basin]])
        self.dao.bulk_insert(new_dtos)
        return profiles_links
    
    def _create_summary(self, basin_catalogs: dict[str, list[Path]]):
        summary = {}
        basin_records = []
        for basin, catalog_paths in basin_catalogs.items():
            wells = {}
            catalog_path = catalog_paths[-1]
            profiles = self.anp_scrapper.fetch_profile_links(catalog_path=catalog_path)
            for profile_type, links in profiles.items():
                for link in links:    
                    match = re.search(r"/POCO/(.*?)/perfil", link, re.IGNORECASE)
                    well = match.group(1).split("/")[-1] # type: ignore
                    file_extension = link.split(".")[-1]
                    if well not in wells:
                        wells[well] = {
                            "composite_count": 0,
                            "conventional_count": 0,
                            "composite_pdf": 0,
                            "conventional_dlis_lis_las": 0,
                            "composite_extensions": set(),
                            "conventional_extensions": set()
                        }
                    p = "composite" if "composite" in profile_type else "conventional"
                    wells[well][f"{p}_count"] += 1
                    wells[well][f"{p}_extensions"].add(file_extension)
                    if file_extension.lower() == "pdf" and p == "composite":
                        wells[well]["composite_pdf"] += 1
                    if file_extension.lower() in ["dlis", "lis", "las"] and p == "conventional":
                        wells[well]["conventional_dlis_lis_las"] += 1
            
            wells_records = [{
                "basin": basin,
                "well": well,
                **data
                } for well, data in wells.items()
            ]
            basin_record = {
                "basin": basin,	
                "total_wells": len(wells_records),
                "total_wells_with_composite": len([well for well, data in wells.items() if data["composite_count"] > 0]),
                "total_wells_with_conventional": len([well for well, data in wells.items() if data["conventional_count"] > 0]),
                "total_wells_with_both": len([well for well, data in wells.items() if data["conventional_count"] > 0 and data["composite_count"] > 0]),
                "total_wells_with_composite_pdf": len([well for well, data in wells.items() if data["composite_pdf"] > 0]),
                "total_wells_with_conventional_dlis_lis_las": len([well for well, data in wells.items() if data["conventional_dlis_lis_las"] > 0]),
                "total_wells_with_composite_and_conventional_dlis_lis_las": len([well for well, data in wells.items() if data["composite_pdf"] > 0 and data["conventional_dlis_lis_las"] > 0]),
                "total_files": sum([len(links) for links in profiles.values()]),
            }
            basin_records.append(basin_record)
            logger.info(f"Basin record: {basin_record}")
        summary_path = Path(self.download_directory) / "summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as file:
            json.dump(basin_records, file, indent=4)
            file.close()
        
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
        dtos = self.dao.fetch_where(f"lower(name) LIKE '%md5%.txt' and status = '{DownloadStatus.WAITING.value}'")
        self.downloader.download(dtos)
        logger.info(":white_check_mark: Done.")
        
        logger.info(":cyclone: Extracting composite and conventional profile urls from catalogs...")
        dtos = self.dao.fetch_where(f"lower(name) LIKE '%md5%.txt'")
        self._fetch_profiles_links(dtos)
        logger.info(":white_check_mark: Done.")
        
        logger.info(":cyclone: Downloading composite and conventional profiles from urls...")
        dtos = self.dao.fetch_where(f"lower(name) NOT LIKE '%md5%.txt' and status = '{DownloadStatus.WAITING.value}'")
        self.downloader.download(dtos[0:10])
        logger.info(":white_check_mark: Done.")
        
        # logger.info(":cyclone: Summarizing...")
        # #self._create_summary(catalogs_path)
        # logger.info(":white_check_mark: Done.")
        