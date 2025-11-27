from abc import ABC, abstractmethod
from typing import NamedTuple

ModelDataset = NamedTuple('ModelDataset', [('train', list), ('train_target', list), ('test', list), ('test_target', list)])

class BaseModel(ABC):
    def __init__(self):
        self.model = None
    
    @abstractmethod
    def train(self, data: ModelDataset) -> None:
        pass
    
    @abstractmethod
    def predict(self, input_data: list) -> list:
        pass
    
    @abstractmethod
    def evaluate(self, test_data: ModelDataset) -> dict:
        pass
    
    @abstractmethod
    def save(self, file_path: str) -> None:
        pass

class FeatureProcessingPolicy(ABC):
    @abstractmethod
    def fetch(self) -> ModelDataset:
        pass


class ModelBuilderEngine(ABC):
    def __init__(self, policy: FeatureProcessingPolicy, model: BaseModel) -> None:
        self.policy: FeatureProcessingPolicy = policy
        self.model: BaseModel = model

    @abstractmethod
    def build(self) -> BaseModel:
        pass
