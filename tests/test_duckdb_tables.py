"""CSV/DuckDB table-store parity tests over tiny committed fixture cycles."""

from __future__ import annotations

from pathlib import Path

from pandas.testing import assert_frame_equal
import pytest

pytest.importorskip("duckdb")

from openNASR.duckdb_builder import (
    DuckDbBuildError,
    SOURCE_TEXT_READ_OPTIONS,
    build_duckdb,
)
from openNASR.duckdb_tables import DuckDbTableRepository
from openNASR.exceptions import TableNotFoundError
from openNASR.tables import TableRepository


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "duckdb_parity"


@pytest.fixture(params=("pre_2026_09", "nasr_2026_09"))
def table_stores(tmp_path: Path, request: pytest.FixtureRequest):
    """Return equivalent CSV and validated DuckDB stores for one generation."""

    generation = str(request.param)
    source = FIXTURE_ROOT / generation / "CSV_Data" / generation
    effective_date = "2026-08-06" if generation == "pre_2026_09" else "2026-09-03"
    database = tmp_path / generation / "nasr.duckdb"
    build_duckdb(source, database, effective_date)
    csv = TableRepository(source, read_options=SOURCE_TEXT_READ_OPTIONS)
    duckdb = DuckDbTableRepository(database)
    try:
        yield csv, duckdb
    finally:
        duckdb.close()


def test_duckdb_store_matches_csv_table_access_and_mapping(table_stores):
    csv, duckdb = table_stores

    assert duckdb.available_tables == csv.available_tables
    assert list(duckdb) == list(csv)
    assert len(duckdb) == len(csv)
    for table in csv:
        assert not duckdb.is_loaded(table)
        expected = csv.load(table)
        actual = duckdb.load(table)
        assert_frame_equal(actual, expected, check_dtype=True)
        assert duckdb[table.lower()] is actual
        assert duckdb.table(table) is actual
        assert duckdb.is_loaded(table.lower())


def test_duckdb_store_matches_csv_copy_and_index_semantics(table_stores):
    csv, duckdb = table_stores

    for store in (csv, duckdb):
        shared = store.table("FIX_BASE")
        isolated = store.table("FIX_BASE", copy=True)
        isolated.loc[0, "FIX_ID"] = "MUTATED"
        assert shared.loc[0, "FIX_ID"] == "DUP"

        exact = store.index("FIX_BASE", "FIX_ID")
        normalized = store.normalized_index("FIX_BASE", "FIX_ID")
        assert exact is store.index("fix_base", "FIX_ID")
        assert normalized is store.normalized_index("fix_base", "FIX_ID")

    assert duckdb.index("FIX_BASE", "FIX_ID") == csv.index("FIX_BASE", "FIX_ID")
    assert duckdb.normalized_index("FIX_BASE", "FIX_ID") == csv.normalized_index(
        "FIX_BASE", "FIX_ID"
    )


def test_duckdb_store_preserves_missing_table_error(table_stores):
    _, duckdb = table_stores

    with pytest.raises(TableNotFoundError, match="MISSING"):
        duckdb.load("missing")
    assert not duckdb.is_loaded("missing")


def test_duckdb_mutation_is_cached_per_instance_without_database_write(tmp_path: Path):
    source = FIXTURE_ROOT / "pre_2026_09" / "CSV_Data" / "pre_2026_09"
    database = tmp_path / "nasr.duckdb"
    result = build_duckdb(source, database, "2026-08-06")
    original_database = database.read_bytes()

    first = DuckDbTableRepository(database)
    try:
        shared = first.table("FIX_BASE")
        original_value = shared.loc[0, "FIX_ID"]
        shared.loc[0, "FIX_ID"] = "IN-MEMORY-ONLY"

        assert first["FIX_BASE"] is shared
        assert first.table("FIX_BASE").loc[0, "FIX_ID"] == "IN-MEMORY-ONLY"
        isolated = first.table("FIX_BASE", copy=True)
        isolated.loc[0, "FIX_ID"] = "COPY-ONLY"
        assert first.table("FIX_BASE").loc[0, "FIX_ID"] == "IN-MEMORY-ONLY"
    finally:
        first.close()

    assert database.read_bytes() == original_database
    second = DuckDbTableRepository(database)
    try:
        assert second.table("FIX_BASE").loc[0, "FIX_ID"] == original_value
    finally:
        second.close()
    assert result.metadata_path.is_file()


def test_duckdb_repository_rejects_database_tampering(tmp_path: Path):
    source = FIXTURE_ROOT / "pre_2026_09" / "CSV_Data" / "pre_2026_09"
    database = tmp_path / "nasr.duckdb"
    build_duckdb(source, database, "2026-08-06")
    with database.open("ab") as output:
        output.write(b"tampered")

    with pytest.raises(DuckDbBuildError, match="metadata sidecar"):
        DuckDbTableRepository(database)
