
# spy/mobile.py

from .base import SpyRunner

class MobileSpyRunner(SpyRunner):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Mobile spy not yet implemented.")
    def start(self): pass
    def stop(self): pass
    def export_repository(self, output_path: str): pass