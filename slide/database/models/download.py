from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Optional
from abc import ABC

from slide.database import BaseDAO, BaseDTO, CustomField

class DownloadStatus(Enum):
    DONE = "done"
    WAITING = "waiting"

class DownloadDTO(BaseDTO):
    url: str = CustomField(primary_key=True)
    path: str
    name: str
    status: str  # "done", "waiting", "failed"
    errors: str | None = None
    headers: str | None = None  # You can store this as JSON string if needed


class DownloadDAO(BaseDAO):
    def __init__(self, db_path: str | Path = "download.db"):
        super().__init__(db_path)
        self.create_table()

    @property
    def conflict_keys(self) -> str:
        return "url"
    
    @property
    def dto_class(self) -> type[DownloadDTO]:
        return DownloadDTO
    
    def upsert(self, dto: DownloadDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[DownloadDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[DownloadDTO]:
        return super().fetch_all(where)
    
    def fetch_where(self, condition: str) -> list[DownloadDTO]:
        return super().fetch_where(condition)

    def fetch_by_url(self, url: str) -> Optional[DownloadDTO]:
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT *
            FROM {self.dto_class.table_name()}
            WHERE url = ?
        """, (url,))
        row = cursor.fetchone()

        columns = [desc[0] for desc in cursor.description]
        if row:
            return self.dto_class(**dict(zip(columns, row)))
        return None
    


class CatalogDownloadDTO(DownloadDTO):
    basin: str
    
    @classmethod
    def table_name(cls) -> str:
        return "catalogs"

class CatalogDownloadDAO(DownloadDAO):
    
    def __init__(self, db_path = "download.db"):
        super().__init__(db_path)

    @property
    def dto_class(self) -> type[CatalogDownloadDTO]:
        return CatalogDownloadDTO

    def upsert(self, dto: CatalogDownloadDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[CatalogDownloadDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[CatalogDownloadDTO]:
        return super().fetch_all(where)

    def fetch_where(self, condition: str) -> list[CatalogDownloadDTO]:
        return super().fetch_where(condition)
    

class ANPDownloadDTO(DownloadDTO):
    basin: str
    well: str


class AGPDownloadDTO(ANPDownloadDTO):
    
    @classmethod
    def table_name(cls) -> str:
        return "agp"
    

class AGPDownloadDAO(DownloadDAO):
    
    @property
    def dto_class(self) -> type[AGPDownloadDTO]:
        return AGPDownloadDTO

    def upsert(self, dto: AGPDownloadDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[AGPDownloadDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[AGPDownloadDTO]:
        return super().fetch_all(where)

    def fetch_where(self, condition: str) -> list[AGPDownloadDTO]:
        return super().fetch_where(condition)
    

class LogDownloadDTO(ANPDownloadDTO):
    
    @classmethod
    def table_name(cls) -> str:
        return "logs"
    
    
class LogDownloadDAO(DownloadDAO):
    
    @property
    def dto_class(self) -> type[LogDownloadDTO]:
        return LogDownloadDTO

    def upsert(self, dto: LogDownloadDTO):
        super().upsert(dto)

    def bulk_insert(self, dtos: list[LogDownloadDTO], ignore_errors: bool = False):
        super().bulk_insert(dtos, ignore_errors)

    def fetch_all(self, where: str | None = None) -> list[LogDownloadDTO]:
        return super().fetch_all(where)

    def fetch_where(self, condition: str) -> list[LogDownloadDTO]:
        return super().fetch_where(condition)
    
    def fetch_from(self, query: str) -> list[LogDownloadDTO]:
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        return [self.dto_class(**dict(zip(columns, row))) for row in rows]