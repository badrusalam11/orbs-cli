"""
orbs - A lightweight Appium framework with structured runner,
report generator, and POM-based test execution. Inspired by Katalon.
"""

__version__ = "0.1.0"

import sys
from pathlib import Path
import yaml

from ._constant import PLATFORM_LIST

from .runner import Runner
from .utils   import Logger
from .config import Config

config = Config()  # global singleton instance


def run(target=None, platform=None):
    logger = Logger.get_logger()
    
    # Use platform from CLI if provided, otherwise use default_platform from config
    if platform:
        current_platform = platform
    else:
        current_platform = config.get('default_platform')
    
    # precondition for mobile testing
    if current_platform in PLATFORM_LIST["mobile"]:
        check_dependencies()

    # grab argument
    if not target:
        if len(sys.argv) < 2:
            logger.error("Usage: python main.py <test_file|test_collection.yml>")
            sys.exit(1)
        target = sys.argv[1]

    p = Path(target)
    if not p.exists():
        logger.error(f"File not found: {p}")
        sys.exit(1)

    runner = Runner()

    # dispatch by extension + content
    suffix = p.suffix.lower()
    if suffix in (".yml", ".yaml"):
        # load minimal YAML to check for 'testsuites'
        try:
            spec = yaml.safe_load(p.read_text())
        except Exception as e:
            logger.error(f"Failed to parse YAML {p}: {e}")
            sys.exit(1)

        if isinstance(spec, dict) and "testsuites" in spec:
            runner.run_suite_collection(str(p))
        else:
            runner.run_suite(str(p))

    elif suffix == ".py":
        runner.run_case(str(p))

    elif suffix == ".feature":
        runner.run_feature(str(p))

    else:
        logger.error(
            "Invalid file type. Provide:\n"
            " • a .yml/.yaml (with top‑level testsuites: → collection)\n"
            " • a .yml/.yaml (no testsuites → single suite)\n"
            " • a .py test case\n"
            " • a .feature file"
        )
        sys.exit(1)

def check_dependencies():
    from orbs.cli import choose_device, ensure_appium_server, get_connected_devices, write_device_property

        # Start Appium server if needed
    ensure_appium_server()

    # Read default deviceName from appium.properties if present
    device_name = config.get("deviceName", "")
    # If a placeholder or empty, prompt selection
    if not device_name or device_name.lower() in ('', 'auto', 'detect'):
        devices = get_connected_devices()
        device_name = choose_device(devices)
        write_device_property(device_name)