# record/base.py

from abc import ABC, abstractmethod

class RecordRunner(ABC):
    """
    Abstract base for all Record Runners.
    """
    @abstractmethod
    def start(self):
        """Initialize and start record session"""
        pass

    @abstractmethod
    def stop(self):
        """Stop recording and generate test case"""
        pass