from pathlib import Path
import sqlite3
from pydantic import BaseModel, Field, JsonValue
from pydantic.fields import FieldInfo
from datetime import datetime
from abc import ABC, abstractmethod

def CustomField(*, primary_key: bool = False, unique: bool = False, nullable: bool = True, **kwargs) -> FieldInfo:
    """
    Custom Field factory function that adds additional constraints and properties like primary key, unique, etc.

    Args:
        primary_key (bool): Whether the field is a primary key.
        unique (bool): Whether the field is unique.
        nullable (bool): Whether the field can be null.
        **kwargs: Additional arguments to pass to the Field constructor.
    Returns:
        FieldInfo: Pydantic Field object with additional constraints
    """
    return Field(json_schema_extra={"primary_key": primary_key, "unique": unique, "nullable": nullable}, **kwargs)


class BaseDTO(BaseModel):
    """
    Base Data Transfer Object (DTO) that enforces attributes to be defined
    using Pydantic's Field and generates a SQL schema including column types
    and constraints (NOT NULL, PRIMARY KEY, UNIQUE).
    """

    def to_dict(self) -> dict:
        """
        Convert the object to a dictionary.
        Returns:
            dict: dictionary with object attributes.
        """
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    @classmethod
    def table_name(cls) -> str:
        """
        Return the table name based on the class name.
        Override this method in subclasses if you want a custom table name.
        """
        return cls.__name__.lower()

    @classmethod
    def table_schema(cls) -> str:
        """
        Generate the schema for creating a table in SQL.
        Returns SQL column definitions with type and constraints like NOT NULL, UNIQUE, PRIMARY KEY.
        """
        field_definitions = []
        for field_name, field in cls.model_fields.items():
            field_type = cls.__map_field_type_to_sql(field)
            constraints = cls.__get_constraints(field)
            sql_field = f"{field_name} {field_type} {constraints}".strip()
            field_definitions.append(sql_field)

        return ", ".join(field_definitions)

    @staticmethod
    def __map_field_type_to_sql(field: FieldInfo) -> str:
        """
        Map Pydantic field types to SQLite/SQL schema types.

        Args:
            field (FieldInfo): Pydantic Field object.
        Returns:
            str: SQL schema type for the field.
        """
        type_map: dict[type, str] = {
            int: "INTEGER",
            float: "REAL",
            str: "TEXT",
            bool: "BOOLEAN",
            datetime: "DATETIME",
        }
        field_type = field.annotation
        return type_map.get(field_type, "TEXT") if field_type in type_map else "TEXT"

    @staticmethod
    def __get_constraints(field: FieldInfo) -> str:
        """
        Get SQL constraints (PRIMARY KEY, UNIQUE, NOT NULL) based on Pydantic Field configuration.

        Args:
            field (FieldInfo): Pydantic Field object.
        Returns:
            str: SQL constraints for the field.
        """
        constraints = []
        json_schema_extra: dict[str, JsonValue] = (
            field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
        )

        if json_schema_extra.get("primary_key", False):
            constraints.append("PRIMARY KEY")

        if json_schema_extra.get("unique", False):
            constraints.append("UNIQUE")

        if not json_schema_extra.get("nullable", True):
            constraints.append("NOT NULL")

        return " ".join(constraints)


class BaseDAO(ABC):
    """Base class for all DAO"""

    def __init__(self, db_path: str | Path = "base.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, timeout=600)

    @property
    def conflict_keys(self) -> str:
        """Return the ON CONFLICT keys for upsert operations"""
        return ""

    @property
    def dto_class(self) -> BaseDTO:
        """Return the DTO class associated with this DAO"""
        pass

    def create_table(self):
        cursor = self.conn.cursor()
        query = f"""
            CREATE TABLE IF NOT EXISTS {self.dto_class.table_name()} (
                {self.dto_class.table_schema()}
            )
        """
        cursor.execute(query)
        self.conn.commit()

    @abstractmethod
    def upsert(self, dto: BaseDTO):
        cursor = self.conn.cursor()
        keys, values = zip(*dto.to_dict().items())
        placeholders = ", ".join("?" for _ in keys)
        cursor.execute(
            f"""
            INSERT INTO {self.dto_class.table_name()} ({", ".join(keys)})
            VALUES ({placeholders})
            ON CONFLICT({self.conflict_keys}) DO UPDATE SET
                {", ".join(f"{key}=excluded.{key}" for key in keys if key not in self.conflict_keys)}
        """,
            values,
        )
        self.conn.commit()

    @abstractmethod
    def bulk_insert(self, dtos: list[BaseDTO], ignore_errors: bool = False):
        dto = dtos[0]
        keys = dto.to_dict().keys()
        placeholders = ", ".join("?" for _ in keys)
        cursor = self.conn.cursor()
        cursor.executemany(
            f"""
            INSERT {"OR IGNORE" if ignore_errors else ""} INTO {self.dto_class.table_name()} ({", ".join(keys)})
            VALUES ({placeholders})
            {(f"ON CONFLICT({self.conflict_keys}) DO UPDATE SET "
                f"{', '.join(
                    f'{key}=excluded.{key}'
                    for key in keys if key not in self.conflict_keys
                )}"
            ) if not ignore_errors else ""}
            """,
            [tuple(dto.to_dict().values()) for dto in dtos],
        )
        self.conn.commit()

    @abstractmethod
    def fetch_all(self, where: str | None = None) -> list[type[BaseDTO]]:
        cursor = self.conn.cursor()
        query = f"SELECT * FROM {self.dto_class.table_name()}"
        params = []
        if where:
            query += f" WHERE {where}"
            params.append(where)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [self.dto_class(**dict(zip(columns, row))) for row in rows]

    @abstractmethod
    def fetch_where(self, condition: str) -> list[BaseDTO]:
        cursor = self.conn.cursor()
        query = f"SELECT * FROM {self.dto_class.table_name()} WHERE {condition}"
        cursor.execute(query)
        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        return [self.dto_class(**dict(zip(columns, row))) for row in rows]

    def clean(self):
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {self.dto_class.table_name()}")
        self.conn.commit()

    def ensure_connection(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, timeout=600)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None