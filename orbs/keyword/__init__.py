# File: orbs/keyword/__init__.py
"""
Orbs keyword packages
Contains high-level keyword libraries for different domains
"""
from .web import find_test_obj, Web
from .api import API
from .mobile import Mobile
from .locator import WebElementEntity
from .failure_handling import FailureHandling

# Expose module-style entry points for migration (as requested):
# from orbs.keyword import web
# from orbs.keyword import api
# from orbs.keyword import mobile
# from . import web as web
# from . import api as api
# from . import mobile as mobile

__all__ = ['Web', 'API', 'Mobile', 'find_test_obj', 'WebElementEntity', 'FailureHandling']
