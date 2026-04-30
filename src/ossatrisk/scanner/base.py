from abc import ABC, abstractmethod

from ossatrisk.http_client import HttpClient


class BaseScanner(ABC):
    def __init__(self):
        self.client = HttpClient()

    @abstractmethod
    def scan(self):
        """Run the scan and return results"""
        pass
