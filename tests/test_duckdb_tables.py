"""CSV/DuckDB table-store parity tests over tiny committed fixture cycles."""

from __future__ import annotations

from pathlib import Path

from pandas.testing import assert_frame_equal
import pytest

from openNASR.duckdb_builder import SOURCE_TEXT_READ_OPTIONS, build_duckdb
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
