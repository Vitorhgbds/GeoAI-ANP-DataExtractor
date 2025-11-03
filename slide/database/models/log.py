from pathlib import Path
from slide.database import BaseDAO, BaseDTO


class LogDTO(BaseDTO):
    well: str
    depth: float
    CALI: float | None = None
    SP: float | None = None
    GR: float | None = None
    DT: float | None = None
    ILD: float | None = None
    RHOB: float | None = None
    NPHI: float | None = None
    DRHO: float | None = None
    MSFL: float | None = None
    SFLU: float | None = None

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
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.dto_class.table_name()} (
            well TEXT,
            channel TEXT,
            total_data FLOAT,
            PRIMARY KEY (well, channel)
            )
        """
        )
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
        return "depth, well"

    @property
    def dto_class(self) -> type[LogDTO]:
        return LogDTO

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.dto_class.table_name()} (
            well TEXT,
            depth FLOAT,
            CALI FLOAT,
            SP FLOAT,
            GR FLOAT,
            DT FLOAT,
            ILD FLOAT,
            RHOB FLOAT,
            NPHI FLOAT,
            DRHO FLOAT,
            MSFL FLOAT,
            SFLU FLOAT,
            PRIMARY KEY (well, depth)
            )
        """
        )
        self.conn.commit()

    def upsert(self, dto: LogDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[LogDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[LogDTO]:
        return super().fetch_all(where)

    def fetch_where(self, condition: str) -> list[LogDTO]:
        return super().fetch_where(condition)
