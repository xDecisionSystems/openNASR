"""Validated provenance metadata for immutable DuckDB NASR cycles.

The sidecar is deliberately independent of the optional :mod:`duckdb` import.
It lets callers reject an incomplete or incompatible artifact before opening a
database and keeps error handling at this trust boundary predictable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping

from .exceptions import ConfigurationError


STORAGE_FORMAT_VERSION = 1
"""The first on-disk DuckDB metadata format supported by openNASR."""

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DuckDbMetadataError(ConfigurationError):
    """Base error for a missing, malformed, or incompatible DuckDB sidecar."""


class DuckDbMetadataIncompleteError(DuckDbMetadataError):
    """Raised when a database sidecar is absent, malformed, or unfinished."""


class DuckDbMetadataDateMismatchError(DuckDbMetadataError):
    """Raised when a DuckDB artifact is not for the requested effective date."""


class DuckDbStorageVersionError(DuckDbMetadataError):
    """Raised when an artifact was created with an unsupported storage format."""


class DuckDbMetadataTableError(DuckDbMetadataError):
    """Raised when metadata does not describe a required NASR table."""


class DuckDbSchemaFingerprintMismatchError(DuckDbMetadataError):
    """Raised when the extracted CSV schema differs from artifact provenance."""


@dataclass(frozen=True)
class DuckDbCycleMetadata:
    """Validated provenance for one completed per-cycle DuckDB database."""

    effective_date: str
    source_schema_fingerprint: str
    duckdb_version: str
    created_at: str
    tables: Mapping[str, int]
    database_sha256: str
    archive_sha256: str | None = None
    storage_format_version: int = STORAGE_FORMAT_VERSION
    complete: bool = True

    def __post_init__(self) -> None:
        _validate_iso_date(self.effective_date)
        if self.storage_format_version != STORAGE_FORMAT_VERSION:
            raise DuckDbStorageVersionError(
                "DuckDB storage format "
                f"{self.storage_format_version!r} is unsupported; expected "
                f"{STORAGE_FORMAT_VERSION}."
            )
        _validate_digest("source_schema_fingerprint", self.source_schema_fingerprint)
        _validate_digest("database_sha256", self.database_sha256)
        if self.archive_sha256 is not None:
            _validate_digest("archive_sha256", self.archive_sha256)
        _validate_created_at(self.created_at)
        _validate_tables(self.tables)
        if self.complete is not True:
            raise DuckDbMetadataIncompleteError(
                "DuckDB metadata does not mark the build as complete."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation of the sidecar."""

        return {
            "archive_sha256": self.archive_sha256,
            "complete": self.complete,
            "created_at": self.created_at,
            "database_sha256": self.database_sha256,
            "duckdb_version": self.duckdb_version,
            "effective_date": self.effective_date,
            "source_schema_fingerprint": self.source_schema_fingerprint,
            "storage_format_version": self.storage_format_version,
            "tables": dict(sorted(self.tables.items())),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DuckDbCycleMetadata":
        """Parse untrusted JSON and raise only typed metadata errors."""

        required = {
            "complete",
            "created_at",
            "database_sha256",
            "duckdb_version",
            "effective_date",
            "source_schema_fingerprint",
            "storage_format_version",
            "tables",
        }
        missing = sorted(required - set(value))
        if missing:
            raise DuckDbMetadataIncompleteError(
                "DuckDB metadata is missing required fields: " + ", ".join(missing)
            )
        try:
            return cls(
                effective_date=_require_str(value["effective_date"], "effective_date"),
                source_schema_fingerprint=_require_str(
                    value["source_schema_fingerprint"], "source_schema_fingerprint"
                ),
                duckdb_version=_require_str(value["duckdb_version"], "duckdb_version"),
                created_at=_require_str(value["created_at"], "created_at"),
                tables=_require_mapping(value["tables"], "tables"),
                database_sha256=_require_str(
                    value["database_sha256"], "database_sha256"
                ),
                archive_sha256=_optional_str(
                    value.get("archive_sha256"), "archive_sha256"
                ),
                storage_format_version=_require_int(
                    value["storage_format_version"], "storage_format_version"
                ),
                complete=value["complete"],
            )
        except DuckDbMetadataError:
            raise
        except (TypeError, ValueError) as error:
            raise DuckDbMetadataIncompleteError(
                "DuckDB metadata has invalid values."
            ) from error

    def validate(
        self,
        *,
        effective_date: str | date | None = None,
        source_schema_fingerprint: str | None = None,
        required_tables: Iterable[str] = (),
    ) -> None:
        """Check a completed sidecar against the caller's exact expectations."""

        if effective_date is not None:
            requested = (
                effective_date.isoformat()
                if isinstance(effective_date, date)
                else _require_str(effective_date, "effective_date")
            )
            if requested != self.effective_date:
                raise DuckDbMetadataDateMismatchError(
                    f"DuckDB artifact is for {self.effective_date}, not {requested}."
                )
        if (
            source_schema_fingerprint is not None
            and source_schema_fingerprint != self.source_schema_fingerprint
        ):
            raise DuckDbSchemaFingerprintMismatchError(
                "DuckDB artifact does not match the extracted CSV schema fingerprint."
            )
        missing = sorted(
            {
                str(table).strip().upper()
                for table in required_tables
                if str(table).strip().upper() not in self.tables
            }
        )
        if missing:
            raise DuckDbMetadataTableError(
                "DuckDB metadata is missing required tables: " + ", ".join(missing)
            )


def read_metadata(path: str | Path, **expectations: Any) -> DuckDbCycleMetadata:
    """Read and validate a DuckDB sidecar without leaking JSON or I/O errors."""

    metadata_path = Path(path)
    try:
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DuckDbMetadataIncompleteError(
            f"DuckDB metadata is unavailable or malformed: {metadata_path}"
        ) from error
    if not isinstance(raw, Mapping):
        raise DuckDbMetadataIncompleteError("DuckDB metadata must be a JSON object.")
    metadata = DuckDbCycleMetadata.from_dict(raw)
    metadata.validate(**expectations)
    return metadata


def write_metadata_atomic(path: str | Path, metadata: DuckDbCycleMetadata) -> Path:
    """Atomically publish a complete sidecar next to a completed database."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(metadata.to_dict(), output, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def _validate_iso_date(value: object) -> None:
    if not isinstance(value, str):
        raise DuckDbMetadataIncompleteError(
            "effective_date must be an ISO date string."
        )
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise DuckDbMetadataIncompleteError(
            "effective_date must be a valid YYYY-MM-DD date."
        ) from error
    if parsed.isoformat() != value:
        raise DuckDbMetadataIncompleteError(
            "effective_date must be a canonical YYYY-MM-DD date."
        )


def _validate_digest(name: str, value: object) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise DuckDbMetadataIncompleteError(
            f"{name} must be a lowercase SHA-256 hex digest."
        )


def _validate_created_at(value: object) -> None:
    if not isinstance(value, str):
        raise DuckDbMetadataIncompleteError(
            "created_at must be an ISO timestamp string."
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise DuckDbMetadataIncompleteError(
            "created_at must be a valid ISO timestamp."
        ) from error
    if parsed.tzinfo is None:
        raise DuckDbMetadataIncompleteError("created_at must include a UTC offset.")


def _validate_tables(tables: Mapping[str, int]) -> None:
    if not isinstance(tables, Mapping) or not tables:
        raise DuckDbMetadataIncompleteError(
            "tables must be a non-empty table-to-row-count object."
        )
    for table, row_count in tables.items():
        if (
            not isinstance(table, str)
            or table != table.strip().upper()
            or not table
            or not isinstance(row_count, int)
            or isinstance(row_count, bool)
            or row_count < 0
        ):
            raise DuckDbMetadataIncompleteError(
                "tables must map canonical non-empty names to non-negative integers."
            )


def _require_str(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise DuckDbMetadataIncompleteError(f"{name} must be a non-empty string.")
    return value


def _optional_str(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, name)


def _require_mapping(value: object, name: str) -> Mapping[str, int]:
    if not isinstance(value, Mapping):
        raise DuckDbMetadataIncompleteError(f"{name} must be a JSON object.")
    return value  # type: ignore[return-value]


def _require_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DuckDbMetadataIncompleteError(f"{name} must be an integer.")
    return value


__all__ = [
    "DuckDbCycleMetadata",
    "DuckDbMetadataDateMismatchError",
    "DuckDbMetadataError",
    "DuckDbMetadataIncompleteError",
    "DuckDbMetadataTableError",
    "DuckDbSchemaFingerprintMismatchError",
    "DuckDbStorageVersionError",
    "STORAGE_FORMAT_VERSION",
    "read_metadata",
    "write_metadata_atomic",
]
