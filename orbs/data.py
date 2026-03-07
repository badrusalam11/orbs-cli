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
    """CSV data container with filtering and querying capabilities."""
    
    def __init__(self, path: str = None, rows: list[dict] = None):
        """Initialize CSVData from file path or existing row data.
        
        Args:
            path: Path to CSV file (relative to data directories)
            rows: Pre-loaded row data for chaining operations
        """
        if path is not None:
            resolved = _resolve_path(path)
            with open(resolved, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self._rows = list(reader)
        elif rows is not None:
            self._rows = rows
        else:
            self._rows = []

    def all(self) -> list[dict]:
        """Get all rows as a list of dictionaries.
        
        Returns:
            List of all row dictionaries
        """
        return self._rows

    def first(self) -> dict | None:
        """Get the first row, regardless of how many rows exist.
        
        Returns:
            First row dictionary, or None if no rows exist
        """
        return self._rows[0] if self._rows else None

    def one(self, **conditions) -> dict:
        """Get exactly one row matching the conditions.
        
        Raises ValueError if 0 or >1 rows match. Use when you expect
        exactly one row to match your criteria.
        
        Args:
            **conditions: Column=value pairs for exact matching
            
        Returns:
            Single matching row dictionary
            
        Raises:
            ValueError: If 0 or multiple rows match conditions
            
        Examples:
            data.one(id="123")  # Must have exactly 1 row with id=123
            data.where(status="active").one()  # One row from filtered results
        """
        if conditions:
            # With conditions: filter first then check
            results = self._filter(**conditions)
        else:
            # No conditions: use current rows
            results = self._rows
        
        if len(results) == 0:
            raise ValueError("No data found for given condition.")
        if len(results) > 1:
            raise ValueError("Multiple rows found. Expected exactly one.")
        return results[0]

    def where(self, **conditions) -> "CSVData":
        """Filter rows by exact column value matches.
        
        All comparisons are string-based. Returns a new CSVData instance
        for method chaining.
        
        Args:
            **conditions: Column=value pairs for exact matching
            
        Returns:
            New CSVData instance with filtered rows
            
        Examples:
            data.where(status="active")  # Single condition
            data.where(status="active", type="admin")  # Multiple conditions
            data.where(scenario="valid").one()  # Chain with one()
        """
        filtered = self._filter(**conditions)
        return CSVData(rows=filtered)

    def _filter(self, **conditions) -> list[dict]:
        """Internal filtering logic."""
        return [
            row
            for row in self._rows
            if all(str(row.get(k)) == str(v) for k, v in conditions.items())
        ]

    def random(self) -> dict | None:
        """Get a random row from the dataset.
        
        Returns:
            Random row dictionary, or None if no rows exist
        """
        return random.choice(self._rows) if self._rows else None


def load_data(path: str) -> CSVData:
    """Load CSV data from file with environment-aware path resolution.
    
    Resolves file paths in priority order:
    1. data.local/<path> (highest priority, for local overrides)
    2. data/<ENV>/<path> (environment-specific data)
    3. data/<path> (default fallback)
    
    Args:
        path: Relative path to CSV file (e.g., "users.csv" or "auth/tokens.csv")
        
    Returns:
        CSVData instance for querying and filtering
        
    Raises:
        FileNotFoundError: If CSV file not found in any data directory
        
    Examples:
        load_data("users.csv").where(role="admin").first()
        load_data("test-cases/login.csv").one(scenario="valid")
    """
    return CSVData(path)
