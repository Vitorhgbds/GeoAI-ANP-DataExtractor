

from pathlib import Path
from typing import Tuple
from slide.database.models.download import DownloadDAO
from slide.downloaders.aria2p import Aria2P
from slide.scrappers import WebScrapperEngine


class LogEngine(WebScrapperEngine):
    
    def __init__(self, auths: list[Tuple[str,str]]) -> None:
        self.download_directory = Path("./downloads")
        self.downloads = DownloadDAO(db_path=Path("./downloads/download.db"))
        self.downloader = Aria2P(cache_dao=self.downloads)
        self.auths = auths

    def collect(self) -> int:
        
        