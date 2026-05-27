from abc import ABC, abstractmethod
import json 
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """模型配置类"""
    api_key: str
    model: str
    base_url: str
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30 
class BaseClient(ABC):
    @abstractmethod
    def __init__(self, config: ModelConfig, threads=10):
        pass

    @abstractmethod
    def generate(self, message, model):
        pass
    
    @abstractmethod
    def stream_generate(self, message, model):
        pass

    @abstractmethod
    def batch_generate(self, messages, model):
        pass

    @abstractmethod
    def batch_stream_generate(self, messages, model):
        pass