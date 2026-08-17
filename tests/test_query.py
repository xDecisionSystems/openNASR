"""Public bounded-query parity for CSV and completed DuckDB cycles."""

from __future__ import annotations

import pytest

from openNASR import (
    InvalidQueryCursorError,
    QueryFieldNotFoundError,
    QueryFilter,
    QueryTableNotFoundError,
    QueryValidationError,
)
from openNASR.cycles import CycleManager
from openNASR.nasr import NASR


@pytest.fixture(params=("pre_2026_09", "nasr_2026_09"))
def query_backends(request, make_nasr_from_fixture):
    """Return equivalent CSV/DuckDB instances from one synthetic cycle."""

    csv, cache_root = make_nasr_from_fixture(f"duckdb_parity/{request.param}")
    CycleManager(cache_root).build_duckdb(csv.effective_date)
    duckdb = NASR(
        cycle=csv.effective_date,
        cache_dir=cache_root,
        storage="duckdb",
    )
    return csv, duckdb


def test_query_preserves_text_filters_projection_and_backend_parity(query_backends):
    csv, duckdb = query_backends
    filters = (
        QueryFilter.eq("arpt_id", "BWI"),
        QueryFilter.eq("treatment_code", ""),
    )
    kwargs = {
        "filters": filters,
        "fields": ("rwy_id", "rwy_len", "site_no"),
    }

    csv_page = csv.query_table(" apt_rwy ", **kwargs)
    duckdb_page = duckdb.query_table(" apt_rwy ", **kwargs)

    _assert_backend_equivalent(csv_page, duckdb_page)
    assert csv_page.table == "APT_RWY"
    assert csv_page.fields == ("RWY_ID", "RWY_LEN", "SITE_NO")
    assert csv_page.rows == (
        {"RWY_ID": "001", "RWY_LEN": "009501", "SITE_NO": "000012345"},
    )
    assert csv_page.storage == "csv"
    assert duckdb_page.storage == "duckdb"


def test_query_cursor_source_order_and_replay_validation(query_backends):
    csv, duckdb = query_backends
    kwargs = {
        "filters": (QueryFilter.in_("FIX_ID", ("DUP", "MISSING")),),
        "fields": ("FIX_ID", "STATE_CODE", "CHARTING_REMARK"),
        "page_size": 1,
    }

    first_csv = csv.query_table("FIX_BASE", **kwargs)
    first_duckdb = duckdb.query_table("FIX_BASE", **kwargs)
    _assert_backend_equivalent(first_csv, first_duckdb)
    assert first_csv.rows[0]["STATE_CODE"] == "MD"
    assert first_csv.next_cursor is not None

    second_csv = csv.query_table("FIX_BASE", cursor=first_csv.next_cursor, **kwargs)
    second_duckdb = duckdb.query_table(
        "FIX_BASE", cursor=first_duckdb.next_cursor, **kwargs
    )
    _assert_backend_equivalent(second_csv, second_duckdb)
    assert second_csv.rows[0]["STATE_CODE"] == "VA"
    assert second_csv.next_cursor is None

    with pytest.raises(InvalidQueryCursorError):
        csv.query_table(
            "FIX_BASE",
            filters=kwargs["filters"],
            fields=kwargs["fields"],
            page_size=2,
            cursor=first_csv.next_cursor,
        )


def test_query_rejects_unknown_table_fields_and_unbounded_inputs(query_backends):
    csv, duckdb = query_backends
    for nasr in (csv, duckdb):
        with pytest.raises(QueryTableNotFoundError):
            nasr.query_table("APT_RWY; DROP TABLE APT_RWY")
        with pytest.raises(QueryFieldNotFoundError):
            nasr.query_table("APT_RWY", fields=("NO_SUCH_FIELD",))
        with pytest.raises(QueryValidationError):
            nasr.query_table("APT_RWY", fields=())
        with pytest.raises(QueryValidationError):
            nasr.query_table("APT_RWY", page_size=0)
        with pytest.raises(QueryValidationError):
            nasr.query_table("APT_RWY", filters=(QueryFilter.in_("RWY_ID", ()),))
        assert not hasattr(nasr, "sql")


def _assert_backend_equivalent(csv_page, duckdb_page) -> None:
    """Storage provenance differs by design; every result value must match."""

    assert csv_page.table == duckdb_page.table
    assert csv_page.fields == duckdb_page.fields
    assert csv_page.rows == duckdb_page.rows
    assert csv_page.effective_date == duckdb_page.effective_date
    assert csv_page.schema_fingerprint == duckdb_page.schema_fingerprint
    assert csv_page.next_cursor == duckdb_page.next_cursor
