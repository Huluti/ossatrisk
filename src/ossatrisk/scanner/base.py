import httpx

from abc import ABC, abstractmethod


class BaseScanner(ABC):
    def __init__(self):
        self.client = httpx.Client(http2=True)

    @abstractmethod
    def scan(self):
        """Run the scan and return results"""
        pass
