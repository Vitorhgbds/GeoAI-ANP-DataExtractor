from pathlib import Path

from slide.database.dataCollectionPolicy import DataCollectionPolicy, DataCollectionPolicy
from slide.database.models.download import AGPDownloadDAO, AGPDownloadDTO, LogDownloadDAO, LogDownloadDTO
from slide.downloaders.aria2p import Aria2P


class LogCollectionPolicy(DataCollectionPolicy):
    def __init__(self, db_path: Path | str, *args, **kwargs):
        super().__init__(db_path, *args, **kwargs)
        self.downloader = Aria2P(overwrite=False, cache_dao=LogDownloadDAO(self.db_path))
        self.dao = LogDownloadDAO(f"{self.db_path}")

    def collect(self) -> list[LogDownloadDTO]:
        
        dtos = self.dao.fetch_from("""
                WITH AGPWells AS (
                    SELECT DISTINCT 
                        replace(
                            regex_replace(
                                '([A-Za-z]*|^0[0-9])0+([A-Za-z0-9])',
                                a.well,'$1$2'),
                            " ", "") AS well
                    FROM AGPLithology a
                    WHERE a.well IS NOT NULL
                ),
                LogsWells AS (
                    SELECT 
                        replace(well,"-","") AS well,
                        url,
                        path,
                        name,
                        errors,
                        headers,
                        basin,
                        status
                    FROM logs
                )
                SELECT 
                    url,
                    path,
                    name,
                    errors,
                    headers,
                    basin,
                    status,
                    well
                FROM LogsWells 
                    INNER JOIN AGPWells 
                    USING(well)
                WHERE LOWER(name) LIKE "%.dlis" 
                    or LOWER(name) LIKE "%.lis" 
                    or LOWER(name) LIKE "%.las";
        """)
        self.downloader.download(dtos)
        return dtos



class AgpCollectionPolicy(DataCollectionPolicy):
    def __init__(self, db_path: Path | str, *args, **kwargs):
        super().__init__(db_path, *args, **kwargs)
        self.dao = AGPDownloadDAO(f"{self.db_path}")

    def collect(self) -> list[AGPDownloadDTO]:
        return self.dao.fetch_all()