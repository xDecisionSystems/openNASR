"""Recreate a database from the archived zip and compare it to the manifest.

The zip is the source of truth and the database is a rebuildable product. This
proves it: nothing but the bucket is needed to get the same tables back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from openNASR.cycles import CycleManager, sha256_file
from openNASR_contract import Bucket, Manifest

from .classairspace import build_class_airspace


@dataclass(frozen=True)
class RebuildReport:
    effective_date: str
    tables_match: bool
    schema_fingerprint_match: bool
    schema_id_match: bool
    class_airspace_rows_match: bool | None = None

    @property
    def ok(self) -> bool:
        return (
            self.tables_match
            and self.schema_fingerprint_match
            and self.schema_id_match
            and self.class_airspace_rows_match is not False
        )


def rebuild_from_bucket(
    bucket: Bucket, manifest: Manifest, cache_dir: Path
) -> RebuildReport:
    """Download the zip named by ``manifest``, build a database, compare."""

    manager = CycleManager(cache_dir)
    archive = manager.archives_dir / (
        f"28DaySubscription_Effective_{manifest.effective_date}.zip"
    )
    archive.parent.mkdir(parents=True, exist_ok=True)
    bucket.get_file(manifest.zip.key, archive)
    if sha256_file(archive) != manifest.zip.sha256:
        archive.unlink(missing_ok=True)
        raise RuntimeError(f"{manifest.zip.key} does not match its manifest hash")
    result = manager.build_duckdb(date.fromisoformat(manifest.effective_date))
    built = result.metadata
    airspace_match = None
    if manifest.class_airspace is not None:
        airspace = manifest.class_airspace
        with TemporaryDirectory(dir=cache_dir) as work:
            directory = Path(work)
            source = directory / "class_airspace.zip"
            bucket.get_file(airspace.source.key, source)
            if sha256_file(source) != airspace.source.sha256:
                raise RuntimeError(
                    f"{airspace.source.key} does not match its manifest hash"
                )
            summary = build_class_airspace(source, directory / "class_airspace.parquet")
            airspace_match = summary.rows == airspace.rows
    return RebuildReport(
        effective_date=manifest.effective_date,
        tables_match=dict(built.tables) == dict(manifest.tables),
        schema_fingerprint_match=(
            built.source_schema_fingerprint == manifest.source_schema_fingerprint
        ),
        schema_id_match=built.schema_id == manifest.schema_id,
        class_airspace_rows_match=airspace_match,
    )
