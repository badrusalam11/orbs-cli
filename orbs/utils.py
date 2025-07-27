# orbs/utils.py

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from .thread_context import get_context
from .config import Config

def load_env(env_path: str = ".env") -> None:
    """Load environment variables from .env."""
    load_dotenv(env_path)


def render_template(template_name: str, context: dict, dest: Path, base_template_dir: Path):
    env = Environment(loader=FileSystemLoader(str(base_template_dir)))
    tpl = env.get_template(template_name)
    content = tpl.render(**context)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)

def check_dependencies():
    from orbs.cli import choose_device, ensure_appium_server, get_connected_devices, write_device_property

        # Start Appium server if needed
    ensure_appium_server()
    config = Config()

    # Read default deviceName from appium.properties if present
    device_name = get_context("device_id", config.get("deviceName", ""))
    
    # If a placeholder or empty, prompt selection
    if not device_name or device_name.lower() in ('', 'auto', 'detect'):
        print("No deviceName set in context or config. Please select a device.")
        devices = get_connected_devices()
        device_name = choose_device(devices)
        write_device_property(device_name)


class Logger:
    @staticmethod
    def get_logger(name: str = __name__) -> logging.Logger:
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
