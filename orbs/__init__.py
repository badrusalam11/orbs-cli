"""
orbs - A lightweight test automation framework with structured runner,
report generator, and POM-based test execution.
"""

__version__ = "0.1.0"

import sys
from pathlib import Path
import yaml

from ._constant import PLATFORM_LIST

from .runner import Runner
from .log   import log
from .dependency import check_dependencies
from orbs.config import config
from .thread_context import set_context, get_context

def run(target=None, platform=None, device_id=None):    
    # Use platform from CLI if provided, otherwise use default_platform from config
    if platform:
        current_platform = platform
    else:
        current_platform = config.get('default_platform')
    
    # Set platform and device_id to thread context
    set_context('platform', current_platform)
    if device_id:
        set_context('device_id', device_id)
    
    # Initialize exit code
    set_context('exit_code', 0)
    
    # precondition for mobile testing
    if current_platform in PLATFORM_LIST["mobile"]:
        check_dependencies()

    # grab argument
    if not target:
        if len(sys.argv) < 2:
            log.error("Usage: python main.py <test_file|test_collection.yml>")
            sys.exit(1)
        target = sys.argv[1]

    p = Path(target)
    if not p.exists():
        log.error(f"File not found: {p}")
        sys.exit(1)

    runner = Runner()

    # dispatch by extension + content
    suffix = p.suffix.lower()
    if suffix in (".yml", ".yaml"):
        # load minimal YAML to check for 'testsuites'
        try:
            spec = yaml.safe_load(p.read_text())
        except Exception as e:
            log.error(f"Failed to parse YAML {p}: {e}")
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
        log.error(
            "Invalid file type. Provide:\n"
            " • a .yml/.yaml (with top‑level testsuites: → collection)\n"
            " • a .yml/.yaml (no testsuites → single suite)\n"
            " • a .py test case\n"
            " • a .feature file"
        )
        sys.exit(1)
    
    # Get exit code from context and exit with it
    exit_code = get_context('exit_code') or 0
    
    # Flush stdout/stderr to ensure all output is sent before exit
    sys.stdout.flush()
    sys.stderr.flush()
    
    sys.exit(exit_code)

