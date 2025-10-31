from abc import ABC, abstractmethod


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