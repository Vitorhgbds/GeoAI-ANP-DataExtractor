from abc import ABC, abstractmethod


class PostProcessingPolicy(ABC):
    @abstractmethod
    def process(self, data: list) -> list:
        pass


class FeatureExtractionEngine(ABC):
    def __init__(self, policy: PostProcessingPolicy) -> None:
        self.policy: PostProcessingPolicy = policy

    @abstractmethod
    def collect(self) -> list:
        pass
