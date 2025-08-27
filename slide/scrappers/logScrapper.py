
from pathlib import Path
import re
from slide.commons import BASE_URL, WELL_URL
from slide.scrappers import Scrapper


class LogScrapper(Scrapper):
    def __init__(self, catalog: Path):
        self.catalog = catalog

    def islogFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)perfil\s*(composto|convencional)", name.strip()))

    def scrap(self) -> list[str]:
        logs = []
        with open(self.catalog, "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                link = line.split("..")[-1].strip()
                if self.islogFile(link):
                    logs.append(BASE_URL + WELL_URL + link.replace(" ", "%20"))
        return logs