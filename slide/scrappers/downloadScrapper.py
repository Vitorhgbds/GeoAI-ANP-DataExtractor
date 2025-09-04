
from abc import ABC, abstractmethod
import re
from slide.commons import BASE_URL, WELL_URL
from slide.database.models.download import DownloadDTO, DownloadStatus
from slide.scrappers import Scrapper


class DownloadScrapper(Scrapper, ABC):
    def __init__(self, catalog: DownloadDTO):
        self.catalog = catalog

    @abstractmethod
    def isTargetFile(self, name: str) -> bool:
        pass

    def scrap(self) -> list[DownloadDTO]:
        logs: list[str] = []
        with open(f"{self.catalog.path}/{self.catalog.name}", "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                link = line.split("..")[-1].strip()
                link = "/".join(link.split("/")[2:])  # Remove the first empty element and basin name.
                if self.isTargetFile(link):
                    logs.append(f"{BASE_URL}{WELL_URL}{link.replace(' ', '%20')}")

        dtos = []
        for log in logs:
            directory_tree = log.split("/POCO/")[-1].split("/")
            path = "/".join(directory_tree[0:-1])
            if BASE_URL in path:
                continue
            dtos.append(DownloadDTO(
                url=log,
                basin=self.catalog.basin,
                name=log.split("/")[-1],
                path=f"{self.catalog.path}/{path}",
                status=DownloadStatus.WAITING,
                headers=self.catalog.headers
            ))

        return dtos 
    

class LogScrapper(DownloadScrapper):
    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)perfil\s*(composto|convencional)", name.strip()))

class AgpScrapper(DownloadScrapper):
    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)agp", name.strip()))
