# File: orbs/config.py
import json
import os
from typing import List
from dotenv import load_dotenv
import glob

class Config:
    def __init__(self, env_file=".env", properties_dir="settings"):
        # Load all .properties files in settings/ directory
        self.properties = {}
        if os.path.isdir(properties_dir):
            for filepath in glob.glob(os.path.join(properties_dir, "*.properties")):
                self._load_properties_file(filepath)
        # Load .env first
        load_dotenv(env_file)

    def _load_properties_file(self, filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                self.properties[key.strip()] = val.strip()

    def get(self, key, default=None) -> str:
        # 1) Try environment variables (.env takes precedence)
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        # 2) Fallback to properties file
        return self.properties.get(key, default)

    def get_list(self, key, default=None, sep=";") -> List:
        raw = self.get(key, "")
        if not raw:
            return default or []
        return [item.strip() for item in raw.split(sep) if item.strip()]
    
    def get_dict(self, key: str, default=None) -> dict:
        raw = self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return default or {}
    
    def get_bool(self, key: str, default=None) -> bool:
        raw = self.get(key)
        if raw is None:
            return default if default is not None else False
        return str(raw).strip().lower() in ("true", "1", "yes", "y", "on")
    
    def get_int(self, key: str, default = None) -> int:
        raw = self.get(key)
        if raw is None:
            return default if default is not None else 0
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default if default is not None else 0

    def get_float(self, key: str, default = None) -> float:
        raw = self.get(key)
        if raw is None:
            return default if default is not None else 0.0
        try:
            return float(raw)
        except (ValueError, TypeError):
            return default if default is not None else 0.0
        

config = Config()   # 👈 singleton DI SINI
