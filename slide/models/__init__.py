from abc import ABC, abstractmethod
from slide.database import DataCollectionPolicy


class BaseModel(ABC):
    
    @abstractmethod
    def train(self, data):
        pass
    
    @abstractmethod
    def predict(self, input_data):
        pass
    
    @abstractmethod
    def evaluate(self, test_data):
        pass
    
    @abstractmethod
    def save(self, file_path):
        pass
    
class PreprocessingPolicy(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def process(self, data):
        # Placeholder for preprocessing logic
        pass
    
    
class ModelBuilder(ABC):

    def __init__(self, model: BaseModel, collector: DataCollectionPolicy, processor: PreprocessingPolicy):
        self.model = model
        self.collector = collector
        self.processor = processor

    @abstractmethod
    def build(self, config):
        pass
    
__all__ = [
    "BaseModel",
    "PreprocessingPolicy",
    "ModelBuilder",
]