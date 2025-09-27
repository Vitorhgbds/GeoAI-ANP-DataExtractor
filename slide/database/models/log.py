
from pathlib import Path
from slide.database.models.base import BaseDAO, BaseDTO


class LogDTO(BaseDTO):
    well: str
    depth: float
    GR: float | None = None
    SP: float | None = None
    CAL: float | None = None
    RLN: float | None = None
    RSN: float | None = None
    RLAT: float | None = None
    DUMM: float | None = None
    DLT: float | None = None
    RHOB: float | None = None
    NPHI: float | None = None
    DT: float | None = None
    MS: float | None = None
    
    @classmethod
    def table_name(cls) -> str:
        return "LogsFeatures"
    
class LogDAO(BaseDAO):
    def __init__(self, db_path: str | Path = "download.db"):
        super().__init__(db_path)
        self.create_table()

    @property
    def conflict_keys(self) -> str:
        return "depth, well"
    
    @property
    def dto_class(self) -> type[LogDTO]:
        return LogDTO
    
    def upsert(self, dto: LogDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[LogDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[LogDTO]:
        return super().fetch_all(where)
    
    def fetch_where(self, condition: str) -> list[LogDTO]:
        return super().fetch_where(condition)