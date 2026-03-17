from abc import ABC, abstractmethod


class BaseScanner(ABC):
    @abstractmethod
    def scan(self):
        """Run the scan and return results"""
        pass
