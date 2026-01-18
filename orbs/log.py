# orbs/log.py
import logging
import sys
import os
import threading
from .thread_context import get_context

# Detect whether to use colors (disable in CI or non-TTY)
USE_COLOR = sys.stdout.isatty() and not os.getenv("CI")


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "",              # Neutral
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[41m", # Red background
    }
    RESET = "\033[0m"
    ACTION_COLOR = "\033[32m"  # Green for actions

    def format(self, record):
        # Special handling for ACTION level - replace levelname
        if hasattr(record, 'is_action') and record.is_action:
            record.levelname = "ACTION"
        
        # Add test_id to the record if available in context
        test_id = get_context('test_id') or 'MAIN'
        record.test_id = test_id
        
        message = super().format(record)
        if not USE_COLOR:
            return message
        
        # Apply green color for ACTION
        if hasattr(record, 'is_action') and record.is_action:
            return f"{self.ACTION_COLOR}{message}{self.RESET}"
        
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{message}{self.RESET}"


class OrbsLogger(logging.Logger):
    """
    Logger that supports:
      log.info("key")
      log.info("key", value)
      log.info("a", b, c)
    """
    def _format_message(self, msg, args):
        if not args:
            return str(msg)
        return " ".join(str(x) for x in (msg, *args))

    def debug(self, msg, *args, **kwargs):
        super().debug(self._format_message(msg, args), **kwargs)

    def info(self, msg, *args, **kwargs):
        super().info(self._format_message(msg, args), **kwargs)

    def warning(self, msg, *args, **kwargs):
        super().warning(self._format_message(msg, args), **kwargs)

    def error(self, msg, *args, **kwargs):
        super().error(self._format_message(msg, args), **kwargs)

    def critical(self, msg, *args, **kwargs):
        super().critical(self._format_message(msg, args), **kwargs)
    
    def action(self, msg, *args, **kwargs):
        """Log keyword actions (e.g., clicks, typing, navigation) with green color"""
        message = self._format_message(msg, args)
        # Use INFO level but mark it as action for custom formatting
        extra = kwargs.get('extra', {})
        extra['is_action'] = True
        kwargs['extra'] = extra
        super().info(message, **kwargs)


# Register custom logger class
logging.setLoggerClass(OrbsLogger)

# Create global logger
log = logging.getLogger("orbs")
log.setLevel(logging.DEBUG)

if not log.handlers:
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColorFormatter(
        "[%(asctime)s][%(test_id)s] %(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    log.addHandler(console_handler)

# Track file handlers per thread (for parallel execution)
_file_handlers_lock = threading.Lock()
_file_handlers = {}  # {test_id: file_handler}

class TestIdFilter(logging.Filter):
    """Filter that only allows logs matching a specific test_id"""
    def __init__(self, test_id):
        super().__init__()
        self.test_id = test_id
    
    def filter(self, record):
        # Only allow logs with matching test_id (or MAIN for global logs)
        record_test_id = getattr(record, 'test_id', 'MAIN')
        return record_test_id == self.test_id

def add_test_file_handler(test_id):
    """Add file handler for specific test ID (thread-safe)"""
    with _file_handlers_lock:
        # Create logs directory if not exists
        os.makedirs("logs", exist_ok=True)
        
        # Create new file handler for this test
        file_handler = logging.FileHandler(f"logs/{test_id}.log", mode='w')
        file_formatter = logging.Formatter(
            "[%(asctime)s][%(test_id)s] %(levelname)s: %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        # Add filter so only matching test_id logs go to this file
        file_handler.addFilter(TestIdFilter(test_id))
        
        log.addHandler(file_handler)
        
        # Store handler by test_id
        _file_handlers[test_id] = file_handler

def remove_test_file_handler():
    """Remove file handler for current test ID (thread-safe)"""
    from .thread_context import get_context
    test_id = get_context('test_id')
    
    if not test_id:
        return
    
    with _file_handlers_lock:
        file_handler = _file_handlers.pop(test_id, None)
        if file_handler:
            log.removeHandler(file_handler)
            file_handler.close()
