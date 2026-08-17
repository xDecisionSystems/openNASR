"""RouteResolver snapshot isolation across CSV and DuckDB table stores."""

from pathlib import Path

import pytest

from openNASR.duckdb_builder import SOURCE_TEXT_READ_OPTIONS
from openNASR.exceptions import AmbiguousRecordError
from openNASR.flightplan import RouteResolver
from openNASR.tables import TableRepository


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "duckdb_parity"


@pytest.fixture(params=("pre_2026_09", "nasr_2026_09"))
def csv_tables(request):
    generation = str(request.param)
    source = FIXTURE_ROOT / generation / "CSV_Data" / generation
    return TableRepository(source, read_options=SOURCE_TEXT_READ_OPTIONS)


def test_route_resolver_snapshot_isolated_from_csv_table_mutation(csv_tables):
    tables = {name: csv_tables.load(name) for name in csv_tables.available_tables}
    resolver = RouteResolver(tables)
    with pytest.raises(AmbiguousRecordError) as raised:
        resolver.path("DUP")
    original = str(raised.value)

    tables["FIX_BASE"].loc[0, "LAT_DECIMAL"] = "10"

    with pytest.raises(AmbiguousRecordError) as raised:
        resolver.path("DUP")
    assert str(raised.value) == original


def test_route_resolver_isolated_between_duckdb_instances(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    del duckdb
    from openNASR.duckdb_builder import build_duckdb
    from openNASR.duckdb_tables import DuckDbTableRepository

    source = FIXTURE_ROOT / "pre_2026_09" / "CSV_Data" / "pre_2026_09"
    database = tmp_path / "nasr.duckdb"
    build_duckdb(source, database, "2026-08-06")
    first = DuckDbTableRepository(database)
    second = DuckDbTableRepository(database)
    try:
        first_tables = {name: first.load(name) for name in first.available_tables}
        second_tables = {name: second.load(name) for name in second.available_tables}
        first_resolver = RouteResolver(first_tables)
        second_resolver = RouteResolver(second_tables)
        first_tables["FIX_BASE"].loc[0, "LAT_DECIMAL"] = "10"

        with pytest.raises(AmbiguousRecordError) as first_error:
            first_resolver.path("DUP")
        with pytest.raises(AmbiguousRecordError) as second_error:
            second_resolver.path("DUP")
        assert str(first_error.value) == str(second_error.value)
        assert second_tables["FIX_BASE"].loc[0, "LAT_DECIMAL"] != "10"
    finally:
        first.close()
        second.close()
