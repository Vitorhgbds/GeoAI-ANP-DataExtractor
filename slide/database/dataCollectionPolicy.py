from abc import ABC, abstractmethod
from pathlib import Path
from slide.database.models.base import BaseDTO

class DataCollectionPolicy(ABC):

    def __init__(self, db_path: Path | str, *args, **kwargs):
        self.db_path = db_path
    
    @abstractmethod
    def collect(self) -> list[BaseDTO]:
        pass

    @abstractmethod
    def save(self, records: list) -> None:
        pass