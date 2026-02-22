# record/__init__.py

from .base import RecordRunner
from .web import WebRecordRunner

__all__ = ['RecordRunner', 'WebRecordRunner']