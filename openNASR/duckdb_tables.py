"""Read-only, lazily materialized NASR tables stored in DuckDB."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
import hashlib
from pathlib import Path

from pandas import DataFrame

from .duckdb_builder import (
    DuckDbBuildError,
    duckdb_metadata_path,
    open_duckdb_read_only,
)
from .duckdb_metadata import DuckDbCycleMetadata, read_metadata
from .exceptions import ConfigurationError, TableNotFoundError
from .tables import normalize_table_name


class DuckDbTableRepository(Mapping[str, DataFrame]):
    """Expose a completed DuckDB artifact through the CSV table-store surface.

    The database is opened read-only and rows are materialized only on first
    access to each table.  Like :class:`~openNASR.tables.TableRepository`, the
    resulting DataFrame is shared within this repository instance; mutating it
    cannot write through to the immutable database.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        metadata: DuckDbCycleMetadata | None = None,
        metadata_path: str | Path | None = None,
    ) -> None:
        """Open a validated, completed database without permitting writes.

        ``metadata`` is useful when a caller has already validated the sidecar.
        Otherwise the required sidecar next to ``database_path`` is read and
        validated here.  Supplying both avoids ambiguity and is rejected.
        """

        if metadata is not None and metadata_path is not None:
            raise ConfigurationError(
                "Specify either DuckDB metadata or metadata_path, not both."
            )

        self.database_path = Path(database_path)
        self.metadata_path = (
            Path(metadata_path)
            if metadata_path is not None
            else duckdb_metadata_path(self.database_path)
        )
        if metadata is None:
            metadata = read_metadata(self.metadata_path)
        if not isinstance(metadata, DuckDbCycleMetadata):
            raise ConfigurationError(
                "DuckDB metadata must be a DuckDbCycleMetadata instance."
            )
        if not self.database_path.is_file():
            raise DuckDbBuildError(
                f"DuckDB artifact was not found: {self.database_path}"
            )
        if _sha256_file(self.database_path) != metadata.database_sha256:
            raise DuckDbBuildError(
                "DuckDB artifact does not match its completed metadata sidecar."
            )

        self.metadata = metadata
        self._available_tables = tuple(sorted(metadata.tables))
        self._cache: dict[str, DataFrame] = {}
        self._indexes: dict[tuple[str, str], dict[str, tuple[int, ...]]] = {}
        self._normalized_indexes: dict[
            tuple[str, str], dict[str, tuple[int, ...]]
        ] = {}
        self._connection = open_duckdb_read_only(self.database_path)
        try:
            self._validate_table_set()
        except Exception:
            self.close()
            raise

    @property
    def available_tables(self) -> tuple[str, ...]:
        """Return canonical table names recorded in validated metadata."""

        return self._available_tables

    def load(self, name: str) -> DataFrame:
        """Materialize a table once and cache its pandas DataFrame."""

        normalized = normalize_table_name(name)
        if normalized not in self._cache:
            if normalized not in self._available_tables:
                raise TableNotFoundError(f"NASR table {normalized!r} was not found")
            try:
                self._cache[normalized] = self._connection.execute(
                    f"SELECT * FROM {_quote_identifier(normalized)} ORDER BY rowid"
                ).fetchdf()
            except Exception as error:
                raise DuckDbBuildError(
                    f"Unable to read NASR table {normalized!r} from DuckDB."
                ) from error
        return self._cache[normalized]

    def table(self, name: str, *, copy: bool = False) -> DataFrame:
        """Return the cached table, optionally as an isolated deep copy."""

        frame = self.load(name)
        return frame.copy(deep=True) if copy else frame

    def is_loaded(self, name: str) -> bool:
        """Return whether ``name`` is cached without materializing it."""

        return normalize_table_name(name) in self._cache

    def index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Build and cache an exact-value row-position index on demand."""

        normalized = normalize_table_name(name)
        key = (normalized, column)
        if key not in self._indexes:
            positions: dict[str, list[int]] = {}
            for position, value in enumerate(self.load(normalized)[column]):
                positions.setdefault(str(value), []).append(position)
            self._indexes[key] = {
                value: tuple(rows) for value, rows in positions.items()
            }
        return self._indexes[key]

    def normalized_index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Build and cache a case-insensitive row-position index on demand."""

        normalized = normalize_table_name(name)
        key = (normalized, column)
        if key not in self._normalized_indexes:
            positions: dict[str, list[int]] = {}
            for position, value in enumerate(self.load(normalized)[column]):
                positions.setdefault(str(value).strip().upper(), []).append(position)
            self._normalized_indexes[key] = {
                value: tuple(rows) for value, rows in positions.items()
            }
        return self._normalized_indexes[key]

    def close(self) -> None:
        """Release the read-only database connection held by this repository."""

        connection = getattr(self, "_connection", None)
        if connection is not None:
            connection.close()
            self._connection = None

    def __enter__(self) -> "DuckDbTableRepository":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __getitem__(self, name: str) -> DataFrame:
        """Provide mapping-style compatibility for legacy table access."""

        return self.load(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self.available_tables)

    def __len__(self) -> int:
        return len(self.available_tables)

    def _validate_table_set(self) -> None:
        try:
            actual = {
                str(name).upper()
                for (name,) in self._connection.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'main'"
                ).fetchall()
            }
        except Exception as error:
            raise DuckDbBuildError(
                "DuckDB artifact table validation failed."
            ) from error
        if actual != set(self._available_tables):
            raise DuckDbBuildError(
                "DuckDB artifact table set does not match its metadata sidecar."
            )


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["DuckDbTableRepository"]
