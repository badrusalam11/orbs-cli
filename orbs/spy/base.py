# spy/base.py

from abc import ABC, abstractmethod

class SpyRunner(ABC):
    """
    Abstract base for all Spy Runners.
    """
    @abstractmethod
    def start(self):
        """Initialize and start spy session"""
        pass

    @abstractmethod
    def stop(self):
        """Cleanup and stop spy session"""
        pass
