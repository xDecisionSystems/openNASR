"""Lightweight table discovery for a normalized NASR cycle."""

from __future__ import annotations

from pathlib import Path


def discover_tables(cycle_path: str | Path) -> tuple[str, ...]:
    """Return CSV table names without opening CSV contents."""

    root = Path(cycle_path)
    return tuple(sorted({path.stem.upper() for path in root.glob("*.csv")}))


class TableRepository:
    """Repository shell exposing filesystem-backed table discovery."""

    def __init__(self, cycle_path: str | Path) -> None:
        self.cycle_path = Path(cycle_path)

    @property
    def available_tables(self) -> tuple[str, ...]:
        return discover_tables(self.cycle_path)


__all__ = ["TableRepository", "discover_tables"]
