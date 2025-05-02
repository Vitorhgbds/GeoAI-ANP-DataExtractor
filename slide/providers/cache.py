
import json
from pathlib import Path
from typing import Any

from slide.logger import Logger
logger = Logger().get_logger()

class CacheProvider:
    def __init__(self, path: Path):
        self.path = path
        self.cache = self.load()
    
    def load(self) -> dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning(f"Cache file not found: {self.path}.")
            self.clean()
            return dict()
    
    def clean(self):
        logger.debug(f"Creating an empty cache at {self.path}.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(dict(), file, indent=4)
            self.cache = dict()
            file.close()

        
    def save(self, content: dict[str, Any]) -> str:
        logger.debug(f"Saving cache at: {self.path}")
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(content, file, indent=4)
            self.cache = content
            return file.name
    
    def bulk_insert(self, content: dict[str, Any]) -> str:
        for k, v in content.items():
            if k in self.cache and isinstance(self.cache[k], list) and isinstance(v, list):
                self.cache[k].extend(v)
            else:
                self.cache[k] = v
        self.save(self.cache)
        
    def fetch(self) -> dict[str, Any]:
        return self.cache