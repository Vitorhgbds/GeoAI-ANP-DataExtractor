from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Optional

@dataclass
class AgpSummaryDTO:
    basin: str
    well: str
    code: str
    rock: str
    meters: float
    percentage: float

@dataclass
class AgpLithologyDTO:
    basin: str
    well: str
    id: str
    top: float
    bottom: float
    rock: str
    color: str
    hue: str
    granulometry: str
    roundness: str

class AgpLithologyDAO:
    def __init__(self, db_path: str | Path = "agp.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Lithology (
            well TEXT,
            basin TEXT,
            top FLOAT,
            bottom FLOAT,
            rock TEXT,
            color TEXT,
            hue TEXT,
            granulometry TEXT,
            roundness TEXT,
            PRIMARY KEY (well, bottom)
            )
        """)
        self.conn.commit()

    def upsert(self, dto: AgpLithologyDTO):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO Lithology (well, basin, top, bottom, rock, color, hue, granulometry, roundness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(well) DO UPDATE SET
                basin=excluded.basin,
                top=excluded.top,
                bottom=excluded.bottom,
                rock=excluded.rock,
                color=excluded.color,
                hue=excluded.hue,
                granulometry=excluded.granulometry,
                roundness=excluded.roundness
        """, (
            dto.well,
            dto.basin,
            dto.top,
            dto.bottom,
            dto.rock,
            dto.color,
            dto.hue,
            dto.granulometry,
            dto.roundness
        ))
        self.conn.commit()

    def bulk_insert(self, dtos: list[AgpLithologyDTO], ignore_errors: bool = False):
        cursor = self.conn.cursor()
        cursor.executemany(f"""
            INSERT {"OR IGNORE" if ignore_errors else ""} INTO Lithology (well, basin, top, bottom, rock, color, hue, granulometry, roundness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            {("ON CONFLICT(well, bottom) DO UPDATE SET "
                "basin=excluded.basin,"
                "top=excluded.top,"
                "rock=excluded.rock,"
                "color=excluded.color,"
                "hue=excluded.hue,"
                "granulometry=excluded.granulometry,"
                "roundness=excluded.roundness") if not ignore_errors else ""}
            """, [
            (
                dto.well,
                dto.basin,
                dto.top,
                dto.bottom,
                dto.rock,
                dto.color,
                dto.hue,
                dto.granulometry,
                dto.roundness
            ) for dto in dtos
        ])
        self.conn.commit()

    def fetch_all(self, filter: str | None = None, param: str | None = None) -> list[AgpLithologyDTO]:
        cursor = self.conn.cursor()
        query = "SELECT basin, well, top, bottom, rock, color, hue, granulometry, roundness FROM Lithology"
        params = []
        if filter and param:
            query += " WHERE " + filter
            params.append(param)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [AgpLithologyDTO(
            basin=row[0],
            well=row[1],
            top=row[2],
            bottom=row[3],
            rock=row[4],
            color=row[5],
            hue=row[6],
            granulometry=row[7],
            roundness=row[8],
        ) for row in rows]

    def fetch_where(self, condition: str) -> list[AgpLithologyDTO]:
        cursor = self.conn.cursor()
        query = f"SELECT basin, well, top, bottom, rock, color, hue, granulometry, roundness FROM Lithology WHERE {condition}"
        cursor.execute(query)
        rows = cursor.fetchall()
        return [AgpLithologyDTO(
            basin=row[0],
            well=row[1],
            top=row[2],
            bottom=row[3],
            rock=row[4],
            color=row[5],
            hue=row[6],
            granulometry=row[7],
            roundness=row[8],
        ) for row in rows]

    def clean(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Lithology")
        self.conn.commit()

    def close(self):
        self.conn.close()


class AgpSummaryDAO:
    def __init__(self, db_path: str | Path = "agp.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Summary (
                well TEXT,
                basin TEXT,
                code TEXT,
                rock TEXT,
                meters FLOAT,
                percentage FLOAT,
                PRIMARY KEY (well, code)
            )
        """)
        self.conn.commit()

    def upsert(self, dto: AgpSummaryDTO):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO Summary (well, basin, code, rock, meters, percentage)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(well, code) DO UPDATE SET
                basin=excluded.basin,
                rock=excluded.rock,
                meters=excluded.meters,
                percentage=excluded.percentage
        """, (
            dto.well,
            dto.basin,
            dto.code,
            dto.rock,
            dto.meters,
            dto.percentage
        ))
        self.conn.commit()
            

    def bulk_insert(self, dtos: list[AgpSummaryDTO], ignore_errors: bool = False):
        cursor = self.conn.cursor()
        cursor.executemany(f"""
            INSERT {"OR IGNORE" if ignore_errors else ""} INTO Summary (well, basin, code, rock, meters, percentage)
            VALUES (?, ?, ?, ?, ?, ?)
            {("ON CONFLICT(well, code) DO UPDATE SET "
                "basin=excluded.basin,"
                "rock=excluded.rock,"
                "meters=excluded.meters,"
                "percentage=excluded.percentage") if not ignore_errors else ""}
            """, [
            (
                dto.well,
                dto.basin,
                dto.code,
                dto.rock,
                dto.meters,
                dto.percentage
            ) for dto in dtos
        ])
        self.conn.commit()

    def fetch_all(self, filter: str | None = None, param: str | None = None) -> list[AgpSummaryDTO]:
        cursor = self.conn.cursor()
        query = "SELECT well, basin, code, rock, meters, percentage FROM Summary"
        params = []
        if filter and param:
            query += " WHERE " + filter
            params.append(param)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [AgpSummaryDTO(
            well=row[0],
            basin=row[1],
            code=row[2],
            rock=row[3],
            meters=row[4],
            percentage=row[5],
        ) for row in rows]
    
    def fetch_where(self, condition: str) -> list[AgpSummaryDTO]:
        cursor = self.conn.cursor()
        query = f"SELECT well, basin, code, rock, meters, percentage FROM Summary WHERE {condition}"
        cursor.execute(query)
        rows = cursor.fetchall()
        return [AgpSummaryDTO(
            well=row[0],
            basin=row[1],
            code=row[2],
            rock=row[3],
            meters=row[4],
            percentage=row[5],
        ) for row in rows]

    def fetch_where(self, condition: str) -> list[AgpSummaryDTO]:
        cursor = self.conn.cursor()
        query = f"SELECT well, basin, code, rock, meters, percentage FROM Summary WHERE {condition}"
        cursor.execute(query)
        rows = cursor.fetchall()
        return [AgpSummaryDTO(
            well=row[0],
            basin=row[1],
            code=row[2],
            rock=row[3],
            meters=row[4],
            percentage=row[5],
        ) for row in rows]
        
    def clean(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Summary")
        self.conn.commit()

    def close(self):
        self.conn.close()