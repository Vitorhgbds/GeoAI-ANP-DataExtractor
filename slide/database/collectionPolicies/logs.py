from pathlib import Path

from slide.database.dataCollectionPolicy import DataCollectionPolicy, DataCollectionPolicy
from slide.database.models.download import LogDownloadDAO, LogDownloadDTO
from slide.database.models.log import LogChannelsDAO, LogChannelsDTO, LogDAO, LogDTO
from slide.collectors import Aria2P

from slide.logger import Logger

logging = Logger()
logger = logging.get_logger()


class LogCollectionPolicy(DataCollectionPolicy):
    def __init__(self, db_path: Path | str, *args, **kwargs):
        super().__init__(db_path, *args, **kwargs)

    def collect(self) -> list[LogDownloadDTO]:
        dao = LogDownloadDAO(f"{self.db_path}")
        downloader = Aria2P(overwrite=False, cache_dao=dao)
        logger.debug("Collecting dlis, lis and las log download files based on AGP well data.")
        dtos = dao.fetch_from(
            """
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
        """
        )
        logger.debug(f"Found {len(dtos)} log files to be downloaded.")
        download_dtos = dtos.copy()
        downloader.download(download_dtos)
        logger.debug(f"Returning {len(dtos)} collected log files.")
        return dtos

    def save(self, records: list[LogDTO] | list[LogChannelsDTO]) -> None:
        dao_class = LogDAO if isinstance(records[0], LogDTO) else LogChannelsDAO
        dao = dao_class(Path(__file__).parent.parent.parent / "features.db")
        dao.bulk_insert(records)
        logger.debug(f"Saved {len(records)} records to the database features.db.")