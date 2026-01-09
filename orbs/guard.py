from functools import wraps
import logging
from orbs.exception import OrbsException
from orbs.config import Config

def orbs_guard(error_cls, context_fn=None):
    """
    error_cls  : subclass of OrbsException
    context_fn : optional function to add context to error message
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)

            # ✅ already Orbs error → pass through
            except OrbsException:
                raise

            # ❌ everything else → normalize here
            except Exception as e:
                # --- 1. read debug flag ---
                try:
                    debug = Config().get("debug", False)
                except Exception:
                    debug = False

                # --- 2. build contextual message ---
                context = ""
                if context_fn:
                    try:
                        context = context_fn(*args, **kwargs)
                    except Exception:
                        pass

                message = (
                    f"{context}: {str(e)}"
                    if context else str(e)
                )

                # --- 3. logging policy ---
                logger = logging.getLogger(fn.__module__)
                if debug:
                    logger.exception(message)   # full traceback
                else:
                    logger.error(message)

                # --- 4. wrap into OrbsException ---
                raise error_cls(message) from e

        return wrapper
    return decorator
