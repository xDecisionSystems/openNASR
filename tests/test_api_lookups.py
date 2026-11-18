"""Airway lookup logic and row compaction, without a database."""

from types import SimpleNamespace

import pytest

from openNASR_api import lookups

BASE = [
    {
        "REGULATORY": "Y",
        "AWY_LOCATION": "D",
        "AWY_ID": "J74",
        "AWY_DESIGNATION": "J",
        "REMARK": "",
    },
    {"REGULATORY": "Y", "AWY_LOCATION": "D", "AWY_ID": "1", "AWY_DESIGNATION": "V"},
]
SEGMENTS = [
    {
        "AWY_ID": "J74",
        "REGULATORY": "Y",
        "AWY_LOCATION": "D",
        "POINT_SEQ": "20",
        "FROM_POINT": "B",
    },
    {
        "AWY_ID": "J74",
        "REGULATORY": "Y",
        "AWY_LOCATION": "D",
        "POINT_SEQ": "10",
        "FROM_POINT": "A",
    },
    {
        "AWY_ID": "J74",
        "REGULATORY": "N",
        "AWY_LOCATION": "D",
        "POINT_SEQ": "10",
        "FROM_POINT": "X",
    },
]


def fake_query(table, *, filters, page_size, cursor):
    source = {"AWY_BASE": BASE, "AWY_SEG_ALT": SEGMENTS}[table]
    rows = [
        row for row in source if all(row.get(f.field, "") == f.value for f in filters)
    ]
    return SimpleNamespace(rows=tuple(rows), next_cursor=None)


def test_airway_is_found_by_full_id_and_its_segments_are_ordered():
    (airway,) = lookups.airways(fake_query, "j74")

    assert airway["base"] == {
        "REGULATORY": "Y",
        "AWY_LOCATION": "D",
        "AWY_ID": "J74",
        "AWY_DESIGNATION": "J",
    }
    assert [s["FROM_POINT"] for s in airway["segments"]] == ["A", "B"]


def test_airway_is_found_by_designation_plus_number():
    (airway,) = lookups.airways(fake_query, "V1")

    assert airway["base"]["AWY_ID"] == "1" and airway["segments"] == []


@pytest.mark.parametrize("identifier", ["", "74", "J-74", "Q999"])
def test_unknown_or_malformed_airways_are_not_found(identifier):
    with pytest.raises(lookups.NotFoundError):
        lookups.airways(fake_query, identifier)


def test_paging_continues_until_the_last_page():
    pages = {
        None: SimpleNamespace(
            rows=({"FIX_ID": "A", "LAT_DECIMAL": "1", "LONG_DECIMAL": "2"},),
            next_cursor="n",
        ),
        "n": SimpleNamespace(
            rows=({"FIX_ID": "A", "LAT_DECIMAL": "3", "LONG_DECIMAL": "4"},),
            next_cursor=None,
        ),
    }

    result = lookups.fixes(lambda t, *, filters, page_size, cursor: pages[cursor], "a")

    assert [r["position"] for r in result] == [
        {"lat": 1.0, "lon": 2.0},
        {"lat": 3.0, "lon": 4.0},
    ]
