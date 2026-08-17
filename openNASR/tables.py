"""Lightweight, lazily loading table discovery for a normalized NASR cycle."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path

from pandas import DataFrame, read_csv

from .exceptions import TableNotFoundError


def discover_tables(cycle_path: str | Path) -> tuple[str, ...]:
    """Return CSV table names without opening CSV contents."""

    root = Path(cycle_path)
    return tuple(sorted({path.stem.upper() for path in root.glob("*.csv")}))


def normalize_table_name(name: str) -> str:
    """Normalize a requested table name to its canonical uppercase form."""

    return name.strip().upper()


class TableRepository(Mapping[str, DataFrame]):
    """Repository shell exposing filesystem-backed table discovery."""

    def __init__(
        self,
        cycle_path: str | Path,
        *,
        read_options: dict[str, object] | None = None,
    ) -> None:
        """Create a repository over ``cycle_path``.

        ``read_options`` are passed to every ``pandas.read_csv`` call for
        this cycle (for example ``dtype=str, keep_default_na=False,
        na_filter=False`` to preserve raw FAA text losslessly). They apply
        uniformly because a cycle's loading policy is decided once, not
        per-table.
        """

        self.cycle_path = Path(cycle_path)
        self._read_options = dict(read_options) if read_options else {}
        self._cache: dict[str, DataFrame] = {}
        self._indexes: dict[tuple[str, str], dict[str, tuple[int, ...]]] = {}
        self._normalized_indexes: dict[tuple[str, str], dict[str, tuple[int, ...]]] = {}

    @property
    def available_tables(self) -> tuple[str, ...]:
        return discover_tables(self.cycle_path)

    def table_path(self, name: str) -> Path:
        return self.cycle_path / f"{normalize_table_name(name)}.csv"

    def load(self, name: str) -> DataFrame:
        """Load a table once and cache its DataFrame for this repository."""

        normalized = normalize_table_name(name)
        if normalized not in self._cache:
            path = self.table_path(normalized)
            if not path.is_file():
                raise TableNotFoundError(f"NASR table {normalized!r} was not found")
            try:
                self._cache[normalized] = read_csv(path, **self._read_options)
            except UnicodeDecodeError:
                self._cache[normalized] = read_csv(
                    path, encoding="latin-1", **self._read_options
                )
        return self._cache[normalized]

    def table(self, name: str, *, copy: bool = False) -> DataFrame:
        """Return the cached table; mutate it only if that shared state is intended.

        Pass ``copy=True`` when callers need an isolated DataFrame.
        """

        frame = self.load(name)
        return frame.copy(deep=True) if copy else frame

    def is_loaded(self, name: str) -> bool:
        return normalize_table_name(name) in self._cache

    def index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Build and cache a row-position index only when requested."""

        normalized = normalize_table_name(name)
        key = (normalized, column)
        if key not in self._indexes:
            index: dict[str, list[int]] = {}
            for position, value in enumerate(self.load(normalized)[column]):
                index.setdefault(str(value), []).append(position)
            self._indexes[key] = {value: tuple(rows) for value, rows in index.items()}
        return self._indexes[key]

    def normalized_index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Build and cache case-insensitive identifier positions."""

        normalized = normalize_table_name(name)
        key = (normalized, column)
        if key not in self._normalized_indexes:
            index: dict[str, list[int]] = {}
            for position, value in enumerate(self.load(normalized)[column]):
                index.setdefault(str(value).strip().upper(), []).append(position)
            self._normalized_indexes[key] = {
                value: tuple(rows) for value, rows in index.items()
            }
        return self._normalized_indexes[key]

    def __getitem__(self, name: str) -> DataFrame:
        """Provide mapping-style compatibility for legacy table access."""

        return self.load(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self.available_tables)

    def __len__(self) -> int:
        return len(self.available_tables)


__all__ = [
    "TableRepository",
    "discover_tables",
    "normalize_table_name",
]
