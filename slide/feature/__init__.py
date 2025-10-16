from abc import ABC, abstractmethod


class FeatureExtractionPolicy(ABC):
    @abstractmethod
    def extract(self, data: list) -> list:
        pass


class FeatureExtractionEngine(ABC):
    def __init__(self, policy: FeatureExtractionPolicy) -> None:
        self.policy: FeatureExtractionPolicy = policy

    @abstractmethod
    def collect(self) -> list:
        pass
