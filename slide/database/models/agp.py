from pathlib import Path
import sqlite3

from slide.database.models.base import BaseDAO, BaseDTO


class AgpSummaryDTO(BaseDTO):
    basin: str | None = None
    well: str | None = None
    code: str | None = None
    rock: str | None = None
    meters: float | None = None
    percentage: float | None = None

    @classmethod
    def table_name(cls) -> str:
        return "AGPSummary"


class AgpLithologyDTO(BaseDTO):
    basin: str | None = None
    well: str | None = None
    id: str | None = None
    top: float | None = None
    bottom: float | None = None
    rock: str | None = None
    color: str | None = None
    hue: str | None = None
    granulometry: str | None = None
    roundness: str | None = None

    @classmethod
    def table_name(cls) -> str:
        return "AGPLithology"


class AgpLithologyDAO(BaseDAO):
    def __init__(self, db_path: str | Path = "agp.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    @property
    def dto_class(self) -> type[AgpLithologyDTO]:
        return AgpLithologyDTO

    @property
    def conflict_keys(self) -> str:
        return "well, bottom"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.dto_class.table_name()} (
            basin TEXT,
            id TEXT,
            well TEXT,
            top FLOAT,
            bottom FLOAT,
            rock TEXT,
            color TEXT,
            hue TEXT,
            granulometry TEXT,
            roundness TEXT,
            PRIMARY KEY (well, bottom)
            )
        """
        )
        self.conn.commit()

    def upsert(self, dto: AgpLithologyDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[AgpLithologyDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[AgpLithologyDTO]:
        return super().fetch_all(where)

    def fetch_where(self, condition: str) -> list[AgpLithologyDTO]:
        return super().fetch_where(condition)


class AgpSummaryDAO(BaseDAO):
    def __init__(self, db_path: str | Path = "agp.db"):
        super().__init__(db_path)
        self.create_table()

    @property
    def dto_class(self) -> type[AgpSummaryDTO]:
        return AgpSummaryDTO

    @property
    def conflict_keys(self) -> str:
        return "well, code"

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.dto_class.table_name()} (
            well TEXT,
            basin TEXT,
            code TEXT,
            rock TEXT,
            meters FLOAT,
            percentage FLOAT,
            PRIMARY KEY (well, code)
            )
        """
        )
        self.conn.commit()

    def upsert(self, dto: AgpSummaryDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[AgpSummaryDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[AgpSummaryDTO]:
        return super().fetch_all(where)

    def fetch_where(self, condition: str) -> list[AgpSummaryDTO]:
        return super().fetch_where(condition)
