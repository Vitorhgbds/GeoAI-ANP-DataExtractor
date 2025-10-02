
from pathlib import Path
from slide.database.models.base import BaseDAO, BaseDTO


class LogDTO(BaseDTO):
    well: str
    depth: float
    channel: str
    value: float

    @classmethod
    def table_name(cls) -> str:
        return "LogsFeatures"
    
class LogChannelsDTO(BaseDTO):
    well: str
    channel: str
    total_data: float

    @classmethod
    def table_name(cls) -> str:
        return "LogsChannels"
    
class LogChannelsDAO(BaseDAO):
    def __init__(self, db_path: str | Path = "features.db"):
        super().__init__(db_path)
        self.create_table()

    @property
    def conflict_keys(self) -> str:
        return "well, channel"
    
    @property
    def dto_class(self) -> type[LogChannelsDTO]:
        return LogChannelsDTO
    
    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.dto_class.table_name()} (
            well TEXT,
            channel TEXT,
            total_data FLOAT,
            PRIMARY KEY (well, channel)
            )
        """)
        self.conn.commit()

    
    def upsert(self, dto: LogDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[LogDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[LogDTO]:
        return super().fetch_all(where)
    
    def fetch_where(self, condition: str) -> list[LogDTO]:
        return super().fetch_where(condition)
    
class LogDAO(BaseDAO):
    def __init__(self, db_path: str | Path = "features.db"):
        super().__init__(db_path)
        self.create_table()

    @property
    def conflict_keys(self) -> str:
        return "depth, well, channel"
    
    @property
    def dto_class(self) -> type[LogDTO]:
        return LogDTO
    
    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.dto_class.table_name()} (
            well TEXT,
            depth FLOAT,
            channel TEXT,
            value FLOAT,
            PRIMARY KEY (well, depth, channel)
            )
        """)
        self.conn.commit()

    
    def upsert(self, dto: LogDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[LogDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[LogDTO]:
        return super().fetch_all(where)
    
    def fetch_where(self, condition: str) -> list[LogDTO]:
        return super().fetch_where(condition)