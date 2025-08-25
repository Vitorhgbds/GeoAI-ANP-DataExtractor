from abc import ABC, abstractmethod
from slide.database.models.download import DownloadDTO


class DownloadPolicy(ABC):

    @abstractmethod
    def download(self, dtos: list[DownloadDTO]) -> list[str]:
        """
        Download files based on the provided DTOs.

        Args:
            dtos (list[DownloadDTO]): The list of download DTOs to process.

        Returns:
            bool: True if the download was successful, False otherwise.
        """
        pass