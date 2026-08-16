"""Lightweight table discovery for a normalized NASR cycle."""

from __future__ import annotations

from pathlib import Path

from pandas import DataFrame, read_csv


def discover_tables(cycle_path: str | Path) -> tuple[str, ...]:
    """Return CSV table names without opening CSV contents."""

    root = Path(cycle_path)
    return tuple(sorted({path.stem.upper() for path in root.glob("*.csv")}))


def normalize_table_name(name: str) -> str:
    """Normalize a requested table name to its canonical uppercase form."""

    return name.strip().upper()


class TableRepository:
    """Repository shell exposing filesystem-backed table discovery."""

    def __init__(self, cycle_path: str | Path) -> None:
        self.cycle_path = Path(cycle_path)
        self._cache: dict[str, DataFrame] = {}

    @property
    def available_tables(self) -> tuple[str, ...]:
        return discover_tables(self.cycle_path)

    def table_path(self, name: str) -> Path:
        return self.cycle_path / f"{normalize_table_name(name)}.csv"

    def load(self, name: str) -> DataFrame:
        """Load a table once and cache its DataFrame for this repository."""

        normalized = normalize_table_name(name)
        if normalized not in self._cache:
            self._cache[normalized] = read_csv(self.table_path(normalized))
        return self._cache[normalized]

    def is_loaded(self, name: str) -> bool:
        return normalize_table_name(name) in self._cache


__all__ = ["TableRepository", "discover_tables", "normalize_table_name"]
