# orbs/utils.py
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from .thread_context import get_context
import importlib.util

def load_env(env_path: str = ".env") -> None:
    """Load environment variables from .env."""
    load_dotenv(env_path)


def render_template(template_name: str, context: dict, dest: Path, base_template_dir: Path):
    env = Environment(loader=FileSystemLoader(str(base_template_dir)))
    tpl = env.get_template(template_name)
    content = tpl.render(**context)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)

def mask_sensitive_text(text):
    """Mask sensitive user input in strings (e.g. passwords) for reports and logs."""
    import re

    if not isinstance(text, str) or not text:
        return text

    lower_text = text.lower()
    if 'password' not in lower_text and 'pwd' not in lower_text:
        return text

    # Mask any quoted values so locator+value strings keep structure
    def _mask_match(m):
        quote = m.group(1)
        return f'{quote}***PASSWORD***{quote}'

    masked = re.sub(r'(["\'])([^"\']*)(["\'])', _mask_match, text)

    # If there were no quotes, keep locator string but show password marker
    if masked == text:
        # preserve path part (e.g. id=password) but not sensitive value; if text wholly value, mask
        return '***PASSWORD***' if 'id=' not in text and 'xpath=' not in text else text

    return masked


def mask_sensitive_value(value, locator=None, secret=False):
    """Mask value if secret flag is set or locator indicates password-like field."""
    if secret:
        return '***PASSWORD***'

    if isinstance(value, str) and locator:
        loc_lower = str(locator).lower()
        if 'password' in loc_lower or 'pwd' in loc_lower:
            return '***PASSWORD***'

    if isinstance(value, str) and isinstance(locator, str):
        # fallback: use existing heuristic in content
        lower = value.lower()
        if 'password' in lower or 'pwd' in lower:
            return '***PASSWORD***'

    return value


def load_module_from_path(path):
        spec = importlib.util.spec_from_file_location("module.name", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod