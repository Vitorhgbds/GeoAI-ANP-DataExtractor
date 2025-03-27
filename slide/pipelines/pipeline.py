from abc import ABC, abstractmethod

class Pipeline(ABC):
    def __init__(self, *args, **kwargs):
        pass
    
    @abstractmethod
    def run(*args, **kwargs):
        pass