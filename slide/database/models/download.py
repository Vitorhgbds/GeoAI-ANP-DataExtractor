from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Optional

class DownloadStatus(Enum):
    DONE = "done"
    WAITING = "waiting"

@dataclass
class DownloadDTO:
    url: str
    path: str
    name: str
    status: DownloadStatus  # "done", "waiting", "failed"
    errors: Optional[str] = None
    headers: Optional[str] = None  # You can store this as JSON string if needed
    basin: Optional[str] = None

class DownloadDAO:
    def __init__(self, db_path: str | Path = "download.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                url TEXT PRIMARY KEY,
                path TEXT,
                name TEXT,
                status TEXT,
                errors TEXT,
                headers TEXT,
                basin TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def upsert_download(self, dto: DownloadDTO):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO downloads (url, path, name, status, errors, headers, basin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                path=excluded.path,
                name=excluded.name,
                status=excluded.status,
                errors=excluded.errors,
                headers=excluded.headers,
                basin=excluded.basin,
                timestamp=CURRENT_TIMESTAMP
        """, (
            dto.url,
            dto.path,
            dto.name,
            dto.status.value,
            json.dumps(dto.errors) if isinstance(dto.errors, dict) else dto.errors,
            json.dumps(dto.headers) if isinstance(dto.headers, dict) else dto.headers,
            dto.basin,
        ))
        self.conn.commit()
        
    def bulk_insert(self, dtos: list[DownloadDTO], ignore_errors: bool = False):
        cursor = self.conn.cursor()
        cursor.executemany(f"""
            INSERT {"OR IGNORE" if ignore_errors else ""} INTO downloads (url, path, name, status, errors, headers, basin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            {("ON CONFLICT(url) DO UPDATE SET "
                "path=excluded.path,"
                "name=excluded.name,"
                "status=excluded.status,"
                "errors=excluded.errors,"
                "headers=excluded.headers,"
                "basin=excluded.basin,"
                "timestamp=CURRENT_TIMESTAMP") if not ignore_errors else ""}
            """, [
            (
                dto.url,
                dto.path,
                dto.name,
                dto.status.value,
                json.dumps(dto.errors) if isinstance(dto.errors, dict) else dto.errors,
                json.dumps(dto.headers) if isinstance(dto.headers, dict) else dto.headers,
                dto.basin,
            ) for dto in dtos
        ])
        self.conn.commit()

    def fetch_all(self, status_filter: str | None = None) -> list[DownloadDTO]:
        cursor = self.conn.cursor()
        query = "SELECT url, path, name, status, errors, headers, basin FROM downloads"
        params = []
        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [DownloadDTO(
            url=row[0],
            path=row[1],
            name=row[2],
            status=DownloadStatus(row[3]),
            errors=json.loads(row[4]) if row[4] else None,
            headers=json.loads(row[5]) if row[5] else None,
            basin=row[6],
        ) for row in rows]
    
    def fetch_where(self, condition: str) -> list[DownloadDTO]:
        cursor = self.conn.cursor()
        query = f"SELECT url, path, name, status, errors, headers, basin FROM downloads WHERE {condition}"
        cursor.execute(query)
        rows = cursor.fetchall()
        return [DownloadDTO(
            url=row[0],
            path=row[1],
            name=row[2],
            status=DownloadStatus(row[3]),
            errors=json.loads(row[4]) if row[4] else None,
            headers=json.loads(row[5]) if row[5] else None,
            basin=row[6],
        ) for row in rows]
        
    def fetch_by_path_and_name(self, path: str, name: str) -> Optional[DownloadDTO]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT url, path, name, status, errors, headers, basin
            FROM downloads
            WHERE path = ? AND name = ?
        """, (path, name))
        row = cursor.fetchone()
        if row:
            return DownloadDTO(
                url=row[0],
                path=row[1],
                name=row[2],
                status=DownloadStatus(row[3]),
                errors=json.loads(row[4]) if row[4] else None,
                headers=json.loads(row[5]) if row[5] else None,
                basin=row[6],
            )
        return None
    
    def fetch_by_url(self, url: str) -> Optional[DownloadDTO]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT url, path, name, status, errors, headers, basin
            FROM downloads
            WHERE url = ?
        """, (url,))
        row = cursor.fetchone()
        if row:
            return DownloadDTO(
                url=row[0],
                path=row[1],
                name=row[2],
                status=DownloadStatus(row[3]),
                errors=json.loads(row[4]) if row[4] else None,
                headers=json.loads(row[5]) if row[5] else None,
                basin=row[6],
            )
        return None
        
    def clean(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM downloads")
        self.conn.commit()

    def close(self):
        self.conn.close()