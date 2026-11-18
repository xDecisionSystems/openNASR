"""Build, validate and publish one cached cycle.

Order matters: the zip, then the DuckDB file, then the manifest. The manifest
is the "validated" marker, so a reader never sees a build that is half
uploaded, and a crash between steps is repaired by running the same publish
again (identical bytes are a no-op, different bytes are refused).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

from openNASR.cycles import CycleManager, sha256_file, validate_archive
from openNASR_contract import (
    ArtifactRef,
    Bucket,
    ClassAirspace,
    Manifest,
    build_keys,
    class_airspace_source_key,
)

from .classairspace import build_class_airspace


BUILDER_VERSION = 2
ARCHIVER_VERSION = "0.2.0"

REQUIRED_TABLES = (
    "APT_BASE",
    "FIX_BASE",
    "NAV_BASE",
    "AWY_BASE",
    "AWY_SEG_ALT",
    "DP_BASE",
    "DP_RTE",
    "STAR_BASE",
    "STAR_RTE",
)
"""Tables the route resolver needs. A build missing one is not published."""


class PublishError(RuntimeError):
    """Raised when a cycle fails validation and must not be published."""


@dataclass(frozen=True)
class PublishResult:
    manifest: Manifest
    already_published: bool


def publish_cycle(
    manager: CycleManager,
    effective_date: date,
    bucket: Bucket,
    *,
    builder: int = BUILDER_VERSION,
    required_tables: Iterable[str] | None = None,
) -> PublishResult:
    """Publish a cycle that is already in ``manager``'s cache."""

    cached = manager.get(effective_date)
    if cached is None or cached.archive_path is None:
        raise PublishError(f"no downloaded archive for {effective_date.isoformat()}")
    archive = cached.archive_path
    try:
        validate_archive(archive)
    except Exception as error:
        raise PublishError(f"archive failed validation: {error}") from error
    zip_sha = sha256_file(archive)
    keys = build_keys(effective_date.isoformat(), zip_sha, builder)

    if bucket.exists(keys.manifest):
        existing = Manifest.from_json(bucket.get_bytes(keys.manifest))
        return PublishResult(existing, already_published=True)

    airspace = manager.download_airspace(effective_date) if builder >= 2 else None
    result = manager.build_duckdb(effective_date)
    metadata = result.metadata
    required = REQUIRED_TABLES if required_tables is None else tuple(required_tables)
    _validate_build(metadata, result.database_path, required)
    db_sha = sha256_file(result.database_path)

    class_airspace = None
    if airspace is not None:
        with TemporaryDirectory(dir=result.database_path.parent) as work:
            parquet = Path(work) / "class_airspace.parquet"
            try:
                summary = build_class_airspace(airspace, parquet)
            except Exception as error:
                raise PublishError(
                    f"Class airspace failed validation: {error}"
                ) from error
            source_sha = sha256_file(airspace)
            source_key = class_airspace_source_key(
                effective_date.isoformat(), zip_sha, source_sha
            )
            parquet_sha = sha256_file(parquet)
            class_airspace = ClassAirspace(
                ArtifactRef(source_key, source_sha, airspace.stat().st_size),
                ArtifactRef(keys.class_airspace, parquet_sha, parquet.stat().st_size),
                summary.rows,
            )
            bucket.put_file(source_key, airspace, source_sha)
            bucket.put_file(keys.class_airspace, parquet, parquet_sha)

    bucket.put_file(keys.zip, archive, zip_sha)
    bucket.put_file(keys.duckdb, result.database_path, db_sha)
    sidecar_sha = sha256_file(result.metadata_path)
    bucket.put_file(keys.sidecar, result.metadata_path, sidecar_sha)
    manifest = Manifest(
        effective_date=effective_date.isoformat(),
        builder=builder,
        zip=ArtifactRef(keys.zip, zip_sha, archive.stat().st_size),
        duckdb=ArtifactRef(keys.duckdb, db_sha, result.database_path.stat().st_size),
        sidecar=ArtifactRef(
            keys.sidecar, sidecar_sha, result.metadata_path.stat().st_size
        ),
        duckdb_version=metadata.duckdb_version,
        schema_id=metadata.schema_id,
        procedure_order=metadata.procedure_order,
        source_schema_fingerprint=metadata.source_schema_fingerprint,
        tables=dict(metadata.tables),
        created_at=datetime.now(timezone.utc).isoformat(),
        archiver_version=ARCHIVER_VERSION,
        class_airspace=class_airspace,
    )
    bucket.put_bytes(keys.manifest, manifest.to_json().encode("utf-8"))
    return PublishResult(manifest, already_published=False)


def _validate_build(metadata, database_path: Path, required: tuple[str, ...]) -> None:
    if metadata.schema_id is None:
        raise PublishError(
            "the FAA schema was not recognized; add it to SchemaCatalog (and declare "
            "its procedure order) before publishing"
        )
    if metadata.procedure_order != "flight_order":
        raise PublishError(
            f"procedure order {metadata.procedure_order!r} is not supported"
        )
    missing = [name for name in required if not metadata.tables.get(name)]
    if missing:
        raise PublishError(
            "required tables are missing or empty: " + ", ".join(missing)
        )
    _smoke_test(database_path, metadata)


def _smoke_test(database_path: Path, metadata) -> None:
    """Open the file read-only and check it holds what the sidecar says."""

    from openNASR.duckdb_builder import open_duckdb_read_only

    try:
        connection = open_duckdb_read_only(database_path)
        try:
            for table, expected in list(metadata.tables.items())[:3]:
                (count,) = connection.execute(
                    f'SELECT count(*) FROM "{table}"'
                ).fetchone()
                if count != expected:
                    raise PublishError(
                        f"{table} holds {count} rows but the sidecar says {expected}"
                    )
        finally:
            connection.close()
    except PublishError:
        raise
    except Exception as error:
        raise PublishError(f"built database failed to open: {error}") from error
