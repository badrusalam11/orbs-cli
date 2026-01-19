# File: orbs/config.py
import json
import os
from typing import List, Any
from dotenv import load_dotenv
import glob
import yaml

class Config:
    def __init__(self, env_file=".env", properties_dir="settings", environments_dir="environments"):
        # Load all .properties files in settings/ directory
        self.properties = {}
        if os.path.isdir(properties_dir):
            for filepath in glob.glob(os.path.join(properties_dir, "*.properties")):
                self._load_properties_file(filepath)
        # Load .env first
        load_dotenv(env_file)
        
        # Load environment configuration
        self.environments_dir = environments_dir
        self.environment_data = {}
        self._load_environment()

    def _load_properties_file(self, filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                self.properties[key.strip()] = val.strip()

    def _load_environment(self):
        """Load environment configuration from YAML files."""
        # Get active environment from ENV variable or default to 'default'
        active_env = os.getenv("ORBS_ENV", "default")
        env_file = os.path.join(self.environments_dir, f"{active_env}.yml")
        
        # Load default first as fallback
        default_file = os.path.join(self.environments_dir, "default.yml")
        if os.path.exists(default_file):
            with open(default_file, "r", encoding="utf-8") as f:
                self.environment_data = yaml.safe_load(f) or {}
        
        # Override with specific environment if different from default
        if active_env != "default" and os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                env_specific = yaml.safe_load(f) or {}
                self._deep_merge(self.environment_data, env_specific)
        
        # Replace environment variable placeholders
        self._replace_env_vars(self.environment_data)
    
    def _deep_merge(self, base: dict, override: dict):
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _replace_env_vars(self, data: Any):
        """Replace ${VAR_NAME} placeholders with environment variables."""
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = self._replace_env_vars(value)
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Replace ${VAR_NAME} with environment variable
            import re
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, data)
            for var_name in matches:
                env_value = os.getenv(var_name, "")
                data = data.replace(f"${{{var_name}}}", env_value)
        return data

    def get(self, key, default=None) -> str:
        # 1) Try environment variables (.env takes precedence) - case insensitive
        # Check both original case and uppercase
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # Try uppercase version if original not found
        if key != key.upper():
            env_value = os.getenv(key.upper())
            if env_value is not None:
                return env_value
        
        # Try lowercase version if original not found
        if key != key.lower():
            env_value = os.getenv(key.lower())
            if env_value is not None:
                return env_value
        
        # 2) Fallback to properties file - case insensitive
        # Try original case first
        if key in self.properties:
            return self.properties[key]
        
        # Try case-insensitive lookup
        key_lower = key.lower()
        for prop_key, prop_value in self.properties.items():
            if prop_key.lower() == key_lower:
                return prop_value
        
        return default

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
    
    def target(self, key: str, default=None) -> Any:
        """
        Get configuration value from environment YAML files.
        Supports nested keys using dot notation: config.target("custom_config.feature_flag_1")
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Configuration value from active environment
            
        Example:
            url = config.target("url")
            api_url = config.target("api_url", "https://default.com")
            feature = config.target("custom_config.feature_flag_1", False)
        """
        # Navigate through nested keys
        keys = key.split(".")
        value = self.environment_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
        

config = Config()   # 👈 singleton DI SINI
