"""Focused tests for DuckDB sidecar validation and immutable ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from pandas import read_csv
from pandas.testing import assert_frame_equal
import pytest

from openNASR.duckdb_builder import (
    DuckDbBuildError,
    DuckDbBuildLockedError,
    build_duckdb,
    duckdb_metadata_path,
    open_duckdb_read_only,
)
from openNASR.duckdb_metadata import (
    DuckDbCycleMetadata,
    DuckDbMetadataDateMismatchError,
    DuckDbMetadataIncompleteError,
    DuckDbMetadataTableError,
    DuckDbSchemaFingerprintMismatchError,
    DuckDbStorageVersionError,
    read_metadata,
    write_metadata_atomic,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "duckdb_parity"
_DIGEST = "a" * 64


def _metadata() -> DuckDbCycleMetadata:
    return DuckDbCycleMetadata(
        effective_date="2026-08-06",
        source_schema_fingerprint=_DIGEST,
        duckdb_version="1.2.2",
        created_at=datetime.now(timezone.utc).isoformat(),
        tables={"APT_RWY": 1, "FIX_BASE": 2},
        database_sha256=_DIGEST,
    )


def _source(generation: str) -> Path:
    return FIXTURE_ROOT / generation / "CSV_Data" / generation


def _read_source(path: Path):
    return read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


def test_metadata_validates_expected_date_schema_and_tables(tmp_path: Path):
    metadata_path = write_metadata_atomic(tmp_path / "nasr.duckdb.json", _metadata())

    metadata = read_metadata(
        metadata_path,
        effective_date="2026-08-06",
        source_schema_fingerprint=_DIGEST,
        required_tables=("APT_RWY",),
    )
    assert metadata.tables == {"APT_RWY": 1, "FIX_BASE": 2}

    with pytest.raises(DuckDbMetadataDateMismatchError):
        read_metadata(metadata_path, effective_date="2026-09-03")
    with pytest.raises(DuckDbSchemaFingerprintMismatchError):
        read_metadata(metadata_path, source_schema_fingerprint="b" * 64)
    with pytest.raises(DuckDbMetadataTableError):
        read_metadata(metadata_path, required_tables=("APT_BASE",))


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("storage_format_version", 99, DuckDbStorageVersionError),
        ("complete", False, DuckDbMetadataIncompleteError),
        ("effective_date", "not-a-date", DuckDbMetadataIncompleteError),
        ("tables", {"APT_RWY": "one"}, DuckDbMetadataIncompleteError),
    ],
)
def test_metadata_parse_failures_are_typed(
    tmp_path: Path, field: str, value: object, error: type[Exception]
):
    data = _metadata().to_dict()
    data[field] = value
    metadata_path = tmp_path / "nasr.duckdb.json"
    metadata_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(error):
        read_metadata(metadata_path)


def test_metadata_sidecar_is_published_atomically(tmp_path: Path):
    metadata_path = tmp_path / "nasr.duckdb.json"
    first = _metadata()
    write_metadata_atomic(metadata_path, first)
    second_data = first.to_dict()
    second_data["database_sha256"] = "b" * 64
    second = DuckDbCycleMetadata.from_dict(second_data)

    write_metadata_atomic(metadata_path, second)

    assert read_metadata(metadata_path).database_sha256 == "b" * 64
    assert not list(tmp_path.glob(".nasr.duckdb.json.*.tmp"))


@pytest.mark.parametrize(
    ("generation", "effective_date"),
    [
        ("pre_2026_09", "2026-08-06"),
        ("nasr_2026_09", "2026-09-03"),
    ],
)
def test_builder_preserves_all_fixture_csv_text(
    tmp_path: Path, generation: str, effective_date: str
):
    source = _source(generation)
    database = tmp_path / "nasr.duckdb"

    result = build_duckdb(source, database, effective_date)

    assert result.database_path == database
    assert result.metadata_path == duckdb_metadata_path(database)
    assert set(result.metadata.tables) == {"APT_RWY", "FIX_BASE"}
    connection = open_duckdb_read_only(database)
    try:
        for table, count in result.metadata.tables.items():
            actual = connection.execute(f'SELECT * FROM "{table}"').fetchdf()
            expected = _read_source(source / f"{table}.csv")
            assert len(actual.index) == count
            assert_frame_equal(actual, expected, check_dtype=True)
    finally:
        connection.close()


def test_builder_rejects_non_text_read_options(tmp_path: Path):
    with pytest.raises(DuckDbBuildError, match="source-text preservation"):
        build_duckdb(
            _source("pre_2026_09"),
            tmp_path / "nasr.duckdb",
            "2026-08-06",
            read_options={"dtype": object},
        )


def test_builder_keeps_previous_completed_artifact_when_new_build_fails(tmp_path: Path):
    database = tmp_path / "nasr.duckdb"
    first = build_duckdb(_source("pre_2026_09"), database, "2026-08-06")
    original_database = database.read_bytes()
    original_sidecar = first.metadata_path.read_bytes()

    with pytest.raises(DuckDbBuildError):
        build_duckdb(
            _source("pre_2026_09"),
            database,
            "2026-08-06",
            read_options={"na_filter": True},
        )

    assert database.read_bytes() == original_database
    assert first.metadata_path.read_bytes() == original_sidecar


def test_builder_cleans_stale_temps_and_rejects_concurrent_lock(tmp_path: Path):
    database = tmp_path / "nasr.duckdb"
    stale_database = tmp_path / ".nasr.duckdb.interrupted.tmp"
    stale_metadata = tmp_path / ".nasr.duckdb.json.interrupted.tmp"
    stale_database.write_text("partial", encoding="utf-8")
    stale_metadata.write_text("partial", encoding="utf-8")
    lock = tmp_path / ".nasr.duckdb.lock"
    lock.write_text("other process", encoding="utf-8")

    with pytest.raises(DuckDbBuildLockedError):
        build_duckdb(_source("pre_2026_09"), database, "2026-08-06")

    lock.unlink()
    build_duckdb(_source("pre_2026_09"), database, "2026-08-06")
    assert not stale_database.exists()
    assert not stale_metadata.exists()


def test_completed_database_is_opened_read_only(tmp_path: Path):
    database = tmp_path / "nasr.duckdb"
    build_duckdb(_source("pre_2026_09"), database, "2026-08-06")

    connection = open_duckdb_read_only(database)
    try:
        with pytest.raises(Exception):
            connection.execute('CREATE TABLE "WRITE_TEST" (id VARCHAR)')
    finally:
        connection.close()


def test_builder_quotes_untrusted_table_identifiers(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "SAFE.csv").write_text("VALUE\nunchanged\n", encoding="utf-8")
    hostile_name = 'ODD"; DROP TABLE SAFE;--'
    (source / f"{hostile_name}.csv").write_text(
        "VALUE\nquoted identifier\n", encoding="utf-8"
    )
    database = tmp_path / "nasr.duckdb"

    result = build_duckdb(source, database, "2026-08-06")

    assert set(result.metadata.tables) == {"SAFE", hostile_name}
    connection = open_duckdb_read_only(database)
    try:
        assert connection.execute('SELECT VALUE FROM "SAFE"').fetchone() == (
            "unchanged",
        )
        quoted = hostile_name.replace('"', '""')
        assert connection.execute(f'SELECT VALUE FROM "{quoted}"').fetchone() == (
            "quoted identifier",
        )
    finally:
        connection.close()
