"""Safe, lossless construction of immutable per-cycle DuckDB artifacts."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import os
from pathlib import Path
import tempfile

from pandas import DataFrame, read_csv

from .exceptions import ConfigurationError
from .duckdb_metadata import DuckDbCycleMetadata, write_metadata_atomic
from .tables import normalize_table_name


SOURCE_TEXT_READ_OPTIONS: dict[str, object] = {
    "dtype": str,
    "keep_default_na": False,
    "na_filter": False,
}
"""Pandas options required to retain raw FAA fields as source text."""


class DuckDbUnavailableError(ConfigurationError):
    """Raised when code requests DuckDB without the optional dependency."""


class DuckDbBuildError(ConfigurationError):
    """Raised when a NASR DuckDB artifact cannot be safely constructed."""


class DuckDbBuildLockedError(DuckDbBuildError):
    """Raised when another process owns the per-cycle build lock."""


@dataclass(frozen=True)
class DuckDbBuildResult:
    """Locations and validated provenance of one published artifact."""

    database_path: Path
    metadata_path: Path
    metadata: DuckDbCycleMetadata


def duckdb_metadata_path(database_path: str | Path) -> Path:
    """Return the required ``nasr.duckdb.json``-style sidecar path."""

    path = Path(database_path)
    return path.with_name(f"{path.name}.json")


def build_duckdb(
    source_path: str | Path,
    database_path: str | Path,
    effective_date: str | date,
    *,
    archive_sha256: str | None = None,
    read_options: Mapping[str, object] | None = None,
) -> DuckDbBuildResult:
    """Build and atomically publish a database from one resolved CSV directory.

    ``source_path`` must already be the directory that directly contains NASR
    CSV files.  This keeps archive/extraction lifecycle ownership in
    :class:`CycleManager`; the builder has no network or archive side effects.
    """

    source = Path(source_path)
    destination = Path(database_path)
    cycle = _canonical_date(effective_date)
    csv_paths = _discover_csv_paths(source)
    options = _source_text_options(read_options)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with _build_lock(destination):
        _clean_stale_temporary_files(destination)
        temporary = _temporary_database_path(destination)
        previous = destination.with_name(f".{destination.name}.previous")
        try:
            metadata = _build_temporary_database(
                csv_paths,
                temporary,
                cycle,
                archive_sha256=archive_sha256,
                read_options=options,
            )
            _validate_database(temporary, metadata)
            # Preserve the completed pair until its replacement sidecar is
            # durable. Readers reject the short digest-mismatch transition;
            # if sidecar publication fails, restore the previous database.
            previous.unlink(missing_ok=True)
            if destination.exists():
                destination.replace(previous)
            try:
                temporary.replace(destination)
                write_metadata_atomic(duckdb_metadata_path(destination), metadata)
            except Exception:
                destination.unlink(missing_ok=True)
                if previous.exists():
                    previous.replace(destination)
                raise
            previous.unlink(missing_ok=True)
            return DuckDbBuildResult(
                database_path=destination,
                metadata_path=duckdb_metadata_path(destination),
                metadata=metadata,
            )
        except (DuckDbBuildError, DuckDbUnavailableError):
            temporary.unlink(missing_ok=True)
            raise
        except Exception as error:
            temporary.unlink(missing_ok=True)
            raise DuckDbBuildError(
                f"Unable to build DuckDB artifact for NASR cycle {cycle}."
            ) from error


def open_duckdb_read_only(database_path: str | Path):
    """Open a completed artifact read-only; this function never creates a file."""

    path = Path(database_path)
    if not path.is_file():
        raise DuckDbBuildError(f"DuckDB artifact was not found: {path}")
    module = _require_duckdb()
    try:
        return module.connect(str(path), read_only=True)
    except Exception as error:
        raise DuckDbBuildError(
            f"Unable to open DuckDB artifact read-only: {path}"
        ) from error


def source_schema_fingerprint(frames: Mapping[str, DataFrame]) -> str:
    """Return a deterministic SHA-256 fingerprint of names and CSV columns."""

    digest = hashlib.sha256()
    for name in sorted(frames):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        for column in frames[name].columns:
            digest.update(str(column).encode("utf-8"))
            digest.update(b"\0")
        digest.update(b"\n")
    return digest.hexdigest()


def _build_temporary_database(
    csv_paths: Mapping[str, Path],
    temporary: Path,
    effective_date: str,
    *,
    archive_sha256: str | None,
    read_options: Mapping[str, object],
) -> DuckDbCycleMetadata:
    module = _require_duckdb()
    frames: dict[str, DataFrame] = {}
    try:
        for name, path in csv_paths.items():
            frames[name] = _read_source_text(path, read_options)
    except Exception as error:
        raise DuckDbBuildError(
            f"Unable to read NASR source CSV files in {temporary.parent}."
        ) from error

    connection = None
    try:
        connection = module.connect(str(temporary))
        for name, frame in frames.items():
            connection.register("_open_nasr_source", frame)
            connection.execute(
                f"CREATE TABLE {_quote_identifier(name)} AS "
                "SELECT * FROM _open_nasr_source"
            )
            connection.unregister("_open_nasr_source")
        connection.close()
        connection = None
    except Exception as error:
        raise DuckDbBuildError(
            "DuckDB could not import the NASR source tables."
        ) from error
    finally:
        if connection is not None:
            connection.close()

    return DuckDbCycleMetadata(
        effective_date=effective_date,
        source_schema_fingerprint=source_schema_fingerprint(frames),
        duckdb_version=str(module.__version__),
        created_at=datetime.now(timezone.utc).isoformat(),
        tables={name: len(frame.index) for name, frame in frames.items()},
        database_sha256=_sha256_file(temporary),
        archive_sha256=archive_sha256,
    )


def _validate_database(path: Path, metadata: DuckDbCycleMetadata) -> None:
    connection = open_duckdb_read_only(path)
    try:
        actual_names = {
            str(name).upper()
            for (name,) in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
        expected_names = set(metadata.tables)
        if actual_names != expected_names:
            raise DuckDbBuildError(
                "DuckDB validation found a different table set than the source CSVs."
            )
        for name, expected_count in metadata.tables.items():
            count = connection.execute(
                f"SELECT COUNT(*) FROM {_quote_identifier(name)}"
            ).fetchone()[0]
            if count != expected_count:
                raise DuckDbBuildError(
                    f"DuckDB validation found {count} rows in {name}; "
                    f"expected {expected_count}."
                )
    except DuckDbBuildError:
        raise
    except Exception as error:
        raise DuckDbBuildError("DuckDB validation query failed.") from error
    finally:
        connection.close()


def _discover_csv_paths(source: Path) -> dict[str, Path]:
    if not source.is_dir():
        raise DuckDbBuildError(
            f"DuckDB source must be a directory containing CSV files: {source}"
        )
    paths: dict[str, Path] = {}
    for path in sorted(source.glob("*.csv")):
        name = normalize_table_name(path.stem)
        previous = paths.get(name)
        if previous is not None:
            raise DuckDbBuildError(
                f"Ambiguous NASR source tables {previous.name!r} and {path.name!r}."
            )
        paths[name] = path
    if not paths:
        raise DuckDbBuildError(f"No NASR CSV files were found in {source}.")
    return paths


def _read_source_text(path: Path, options: Mapping[str, object]) -> DataFrame:
    try:
        return read_csv(path, **options)
    except UnicodeDecodeError:
        return read_csv(path, encoding="latin-1", **options)


def _source_text_options(
    supplied: Mapping[str, object] | None,
) -> dict[str, object]:
    options = dict(supplied or {})
    for name, required in SOURCE_TEXT_READ_OPTIONS.items():
        if name in options and options[name] != required:
            raise DuckDbBuildError(
                f"DuckDB source-text preservation requires {name}={required!r}."
            )
        options[name] = required
    return options


@contextmanager
def _build_lock(database_path: Path) -> Iterator[Path]:
    lock_path = database_path.with_name(f".{database_path.name}.lock")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise DuckDbBuildLockedError(
            f"Another process is already building {database_path.name}."
        ) from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as lock:
            lock.write(f"pid={os.getpid()}\n")
            lock.flush()
        yield lock_path
    finally:
        lock_path.unlink(missing_ok=True)


def _temporary_database_path(destination: Path) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    # DuckDB requires creating the database itself, not reusing an empty file.
    temporary.unlink()
    return temporary


def _clean_stale_temporary_files(destination: Path) -> None:
    for path in destination.parent.glob(f".{destination.name}.*.tmp"):
        path.unlink(missing_ok=True)
    sidecar = duckdb_metadata_path(destination)
    for path in sidecar.parent.glob(f".{sidecar.name}.*.tmp"):
        path.unlink(missing_ok=True)


def _canonical_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise DuckDbBuildError("NASR effective_date must be an ISO YYYY-MM-DD string.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise DuckDbBuildError(
            "NASR effective_date must be a valid YYYY-MM-DD date."
        ) from error
    if parsed.isoformat() != value:
        raise DuckDbBuildError(
            "NASR effective_date must be a canonical YYYY-MM-DD date."
        )
    return value


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _require_duckdb():
    try:
        import duckdb
    except ImportError as error:
        raise DuckDbUnavailableError(
            "DuckDB support is optional; install openNASR with `.[duckdb]`."
        ) from error
    return duckdb


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "DuckDbBuildError",
    "DuckDbBuildLockedError",
    "DuckDbBuildResult",
    "DuckDbUnavailableError",
    "SOURCE_TEXT_READ_OPTIONS",
    "build_duckdb",
    "duckdb_metadata_path",
    "open_duckdb_read_only",
    "source_schema_fingerprint",
]
