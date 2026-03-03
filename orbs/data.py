"""
data.py

CSV fixture loader for Orbs.

Design principles:
- Read-only
- Exact match filtering only
- Lightweight (no mini ORM)
- Deterministic path resolution
- Uses Orbs config system (not os.getenv)

Resolution priority:
1. data.local/<path>
2. data/<ENV>/<path>
3. data/<path>
"""

from pathlib import Path
import csv
import random

from orbs.config import config


def _get_env():
    """
    Retrieve active environment from Orbs config layer.
    """
    return config.get("ORBS_ENV")


def _resolve_path(relative_path: str) -> Path:
    relative_path = relative_path.strip("/")

    candidates = []

    # 1. data.local (highest priority)
    candidates.append(Path("data.local") / relative_path)

    # 2. data/<ENV>
    env = _get_env()
    if env:
        candidates.append(Path("data") / env / relative_path)

    # 3. default data/
    candidates.append(Path("data") / relative_path)

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"CSV not found. Tried: {', '.join(str(p) for p in candidates)}"
    )


class CSVData:
    def __init__(self, path: str):
        resolved = _resolve_path(path)
        with open(resolved, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self._rows = list(reader)

    def all(self) -> list[dict]:
        return self._rows

    def first(self) -> dict | None:
        return self._rows[0] if self._rows else None

    def one(self, **conditions) -> dict:
        results = self.where(**conditions)
        if len(results) == 0:
            raise ValueError("No data found for given condition.")
        if len(results) > 1:
            raise ValueError("Multiple rows found. Expected exactly one.")
        return results[0]

    def where(self, **conditions) -> list[dict]:
        """
        Exact match only.
        All comparisons are string-based.
        """
        filtered = [
            row
            for row in self._rows
            if all(str(row.get(k)) == str(v) for k, v in conditions.items())
        ]
        return filtered

    def random(self) -> dict | None:
        return random.choice(self._rows) if self._rows else None


def load_data(path: str) -> CSVData:
    return CSVData(path)
