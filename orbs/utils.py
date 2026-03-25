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

    # If there were no quotes, just return generic masked label
    if masked == text:
        return '***PASSWORD***'

    return masked


def load_module_from_path(path):
        spec = importlib.util.spec_from_file_location("module.name", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod