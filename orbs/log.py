# orbs/log.py
import logging
import sys
import os


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
    handler = logging.StreamHandler(sys.stdout)
    formatter = ColorFormatter(
        "[%(asctime)s] %(levelname)s: %(message)s"
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)
