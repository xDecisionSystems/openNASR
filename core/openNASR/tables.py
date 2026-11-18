"""Table-name helpers for FAA NASR CSV sources (used by the DuckDB builder)."""

from __future__ import annotations

from pathlib import Path


def discover_tables(cycle_path: str | Path) -> tuple[str, ...]:
    """Return CSV table names without opening CSV contents."""

    root = Path(cycle_path)
    return tuple(sorted({path.stem.upper() for path in root.glob("*.csv")}))


def normalize_table_name(name: str) -> str:
    """Normalize a requested table name to its canonical uppercase form."""

    return name.strip().upper()


__all__ = [
    "discover_tables",
    "normalize_table_name",
]
