from abc import ABC, abstractmethod
import re
from slide.commons import BASE_URL, WELL_URL
from slide.database.models.download import (
    AGPDownloadDTO,
    ANPDownloadDTO,
    CatalogDownloadDTO,
    DownloadDAO,
    DownloadStatus,
    LogDownloadDTO,
)
from . import Scrapper


class FileScrapper(Scrapper, ABC):
    def __init__(self, catalog: CatalogDownloadDTO):
        self.catalog = catalog

    @abstractmethod
    def isTargetFile(self, name: str) -> bool:
        pass

    @property
    def downloadDTO(self) -> ANPDownloadDTO:
        return ANPDownloadDTO

    @property
    def downloadDAO(self) -> DownloadDAO:
        return DownloadDAO

    def scrap(self) -> list[ANPDownloadDTO]:
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
            dtos.append(
                self.downloadDTO(
                    url=log,
                    basin=self.catalog.basin,
                    name=log.split("/")[-1],
                    path=f"{self.catalog.path}/{path}",
                    status=DownloadStatus.WAITING,
                    headers=self.catalog.headers,
                    well=log.split("/")[-3],
                )
            )

        return dtos


class LogScrapper(FileScrapper):
    @property
    def downloadDTO(self) -> LogDownloadDTO:
        return LogDownloadDTO

    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)perfil\s*(composto|convencional)", name.strip()))


class ConventionalLogScrapper(LogScrapper):
    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)perfil\s*convencional", name.strip()))


class CompositeLogScrapper(LogScrapper):
    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)perfil\s*composto", name.strip()))


class AgpScrapper(FileScrapper):
    @property
    def downloadDTO(self) -> AGPDownloadDTO:
        return AGPDownloadDTO

    def isTargetFile(self, name: str) -> bool:
        return bool(re.search(r"(?i)agp", name.strip()))
