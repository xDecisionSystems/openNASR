"""Internal table-store contract shared by NASR storage backends.

The protocol deliberately describes the small surface consumed by the NASR
facade.  Concrete stores remain responsible for their own loading mechanism;
in particular, CSV decoding options and DuckDB connections are not part of
this contract.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from pandas import DataFrame


class TableStore(Protocol):
    """Minimal lazy table-store interface used by :class:`NASR`.

    Implementations expose cached pandas frames and preserve source row
    order.  The explicit mapping methods preserve the legacy ``[]``,
    iteration, and length adapters; the remaining methods cover the
    table-store behavior shared by filesystem and database implementations.
    """

    def __getitem__(self, name: str) -> DataFrame:
        """Return a table through the legacy mapping access path."""

    def __iter__(self) -> Iterator[str]:
        """Iterate over available canonical table names."""

    def __len__(self) -> int:
        """Return the number of available tables."""

    @property
    def available_tables(self) -> tuple[str, ...]:
        """Return the stable, canonical names available in this store."""

    def load(self, name: str) -> DataFrame:
        """Lazily load and cache a table, raising the typed missing-table error."""

    def table(self, name: str, *, copy: bool = False) -> DataFrame:
        """Return a cached frame, optionally as an isolated deep copy."""

    def is_loaded(self, name: str) -> bool:
        """Return whether a table is already cached without loading it."""

    def index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Return a lazily cached exact-value to row-position index."""

    def normalized_index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Return a lazily cached normalized-value to row-position index."""


__all__ = ["TableStore"]
