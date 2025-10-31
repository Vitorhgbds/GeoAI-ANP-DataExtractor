from abc import ABC, abstractmethod


class PostProcessingPolicy(ABC):
    @abstractmethod
    def process(self, data: list) -> list:
        pass


class FeatureExtractor(ABC):
    def __init__(self, processor: PostProcessingPolicy) -> None:
        self.processor: PostProcessingPolicy = processor

    @abstractmethod
    def extract(self) -> list:
        pass
