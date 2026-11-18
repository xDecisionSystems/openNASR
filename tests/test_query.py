"""Public bounded-query behavior over DuckDB cycles."""

from __future__ import annotations

import pytest

pytest.importorskip("duckdb")

from openNASR import (
    InvalidQueryCursorError,
    QueryFieldNotFoundError,
    QueryFilter,
    QueryTableNotFoundError,
    QueryValidationError,
)


@pytest.fixture(params=("pre_2026_09", "nasr_2026_09"))
def nasr(request, make_nasr_from_fixture):
    """Return a NASR instance for one synthetic cycle."""

    instance, _ = make_nasr_from_fixture(f"duckdb_parity/{request.param}")
    return instance


def test_query_preserves_text_filters_and_projection(nasr):
    filters = (
        QueryFilter.eq("arpt_id", "BWI"),
        QueryFilter.eq("treatment_code", ""),
    )
    page = nasr.query_table(
        " apt_rwy ", filters=filters, fields=("rwy_id", "rwy_len", "site_no")
    )

    assert page.table == "APT_RWY"
    assert page.fields == ("RWY_ID", "RWY_LEN", "SITE_NO")
    assert page.rows == (
        {"RWY_ID": "001", "RWY_LEN": "009501", "SITE_NO": "000012345"},
    )
    assert page.storage == "duckdb"


def test_query_cursor_source_order_and_replay_validation(nasr):
    kwargs = {
        "filters": (QueryFilter.in_("FIX_ID", ("DUP", "MISSING")),),
        "fields": ("FIX_ID", "STATE_CODE", "CHARTING_REMARK"),
        "page_size": 1,
    }

    first = nasr.query_table("FIX_BASE", **kwargs)
    assert first.rows[0]["STATE_CODE"] == "MD"
    assert first.next_cursor is not None

    second = nasr.query_table("FIX_BASE", cursor=first.next_cursor, **kwargs)
    assert second.rows[0]["STATE_CODE"] == "VA"
    assert second.next_cursor is None

    with pytest.raises(InvalidQueryCursorError):
        nasr.query_table(
            "FIX_BASE",
            filters=kwargs["filters"],
            fields=kwargs["fields"],
            page_size=2,
            cursor=first.next_cursor,
        )


def test_query_rejects_unknown_table_fields_and_unbounded_inputs(nasr):
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
