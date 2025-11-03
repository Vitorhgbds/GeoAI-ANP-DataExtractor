from pathlib import Path

from slide.database.dataCollectionPolicy import DataCollectionPolicy, DataCollectionPolicy
from slide.database.models.agp import AgpLithologyDTO, AgpSummaryDAO, AgpSummaryDTO, AgpLithologyDAO
from slide.database.models.download import AGPDownloadDAO, AGPDownloadDTO

from slide.logger import Logger

logging = Logger()
logger = logging.get_logger()

class AgpCollectionPolicy(DataCollectionPolicy):
    def __init__(self, db_path: Path | str, *args, **kwargs):
        super().__init__(db_path, *args, **kwargs)

    def collect(self) -> list[AGPDownloadDTO]:
        dao = AGPDownloadDAO(f"{self.db_path}")
        return dao.fetch_all()

    def save(self, records: list[AgpSummaryDTO] | list[AgpLithologyDTO]) -> None:
        dao_class = AgpLithologyDAO if isinstance(records[0], AgpLithologyDTO) else AgpSummaryDAO
        dao = dao_class(f"{self.db_path}")
        dao.bulk_insert(records)

        dao = dao_class(Path(__file__).parent.parent.parent / "features.db")
        dao.bulk_insert(records)
