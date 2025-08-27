
from abc import ABC, abstractmethod
from pathlib import Path
import re
from slide.commons import BASE_URL, WELL_URL
from slide.database.models.download import DownloadDTO, DownloadStatus
from slide.scrappers import Scrapper


class FileScrapper(Scrapper, ABC):
    def __init__(self, catalog: DownloadDTO):
        self.catalog = catalog

    @abstractmethod
    def isTargetFile(self, name: str) -> bool:
        pass

    def scrap(self) -> list[str]:
        logs: list[str] = []
        with open(self.catalog.path + "/" + self.catalog.name, "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                link = line.split("..")[-1].strip()
                if self.isTargetFile(link):
                    logs.append(BASE_URL + WELL_URL + link.replace(" ", "%20"))

        dtos = []
        for log in logs:
            directory_tree = log.split("/POCO/")[-1].split("/")
            path = "/".join(directory_tree[0:])
            dtos.append(DownloadDTO(
                url=log,
                basin=self.catalog.basin,
                name=log.split("/")[-1],
                path=self.catalog.path + "/" + path,
                status=DownloadStatus.WAITING,
                headers=self.catalog.headers
            ))

        return dtos 
    

class LogScrapper(FileScrapper):
    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)perfil\s*(composto|convencional)", name.strip()))

class AgpScrapper(FileScrapper):
    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)perfil\s*agregado", name.strip()))