"""Airway lookup logic and row compaction, without a database."""

from types import SimpleNamespace

import pytest

from openNASR.exceptions import RecordNotFoundError
from openNASR.query import QueryTableNotFoundError
from openNASR_api import lookups


def test_airport_localizer_wedge_extends_outbound_from_the_runway():
    site = {"SITE_NO": "123", "SITE_TYPE_CODE": "A"}
    tables = {
        "APT_BASE": [{**site, "ARPT_ID": "TST", "ICAO_ID": "KTST"}],
        "APT_RWY": [],
        "APT_RWY_END": [
            {**site, "RWY_END_ID": "09", "LAT_DECIMAL": "40", "LONG_DECIMAL": "-75"},
        ],
        "ILS_BASE": [
            {
                **site,
                "RWY_END_ID": "09",
                "ILS_LOC_ID": "TST",
                "LAT_DECIMAL": "40",
                "LONG_DECIMAL": "-74.98",
                "APCH_BEAR": "95",
                "MAG_VAR": "5",
                "MAG_VAR_HEMIS": "W",
            },
            {**site, "RWY_END_ID": "27", "ILS_LOC_ID": "OTHER"},
        ],
    }

    def query(table, *, filters, page_size, cursor):
        rows = [
            row
            for row in tables[table]
            if all(row.get(f.field) == f.value for f in filters)
        ]
        return SimpleNamespace(rows=rows, next_cursor=None)

    localizer, incomplete = lookups.airport(query, "KTST")["localizers"]
    assert localizer["position"] == {"lat": 40, "lon": -74.98}
    near_left, far_left, far_right, near_right = localizer["wedge"]
    assert near_left["lon"] == pytest.approx(-75)
    assert near_right["lon"] == pytest.approx(-75)
    assert far_left["lon"] < -75.4
    assert far_right["lon"] < -75.4
    assert abs(far_left["lat"] - far_right["lat"]) > 10 * abs(
        near_left["lat"] - near_right["lat"]
    )
    assert incomplete["position"] is None and incomplete["wedge"] == []


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


def test_airway_plot_keeps_gaps_and_unresolved_waypoints():
    segments = [
        {
            "POINT_SEQ": "10",
            "FROM_POINT": "A",
            "FROM_PT_TYPE": "VOR",
            "TO_POINT": "B",
            "AWY_SEG_GAP_FLAG": "Y",
        },
        {"POINT_SEQ": "20", "FROM_POINT": "B", "TO_POINT": "MISSING"},
        {"POINT_SEQ": "30", "FROM_POINT": "MISSING"},
    ]

    def locate(name, point_type):
        if name == "MISSING":
            raise RecordNotFoundError(entity_type="waypoint", identifier=name)
        return (40.0, -75.0 if name == "A" else -74.0)

    first, second, terminal = lookups.airway_plot_segments(segments, locate)
    assert first["gap"]
    assert first["start"]["position"] == {"lat": 40, "lon": -75}
    assert first["end"]["position"] == {"lat": 40, "lon": -74}
    assert second["end"]["position"] is None
    assert second["end"]["issue"]
    assert terminal["end"] is None


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


@pytest.mark.parametrize(
    "lookup,prefix,code,name,computer_code",
    [
        (lookups.arrivals, "STAR", "STAR_COMPUTER_CODE", "ARRIVAL_NAME", "TEST.TEST5"),
        (lookups.departures, "DP", "DP_COMPUTER_CODE", "DP_NAME", "TEST5.TEST"),
    ],
)
def test_procedure_short_codes_and_ordered_points(
    lookup, prefix, code, name, computer_code
):
    key = {code: computer_code, name: "TEST", "ARTCC": "ZAA"}
    tables = {
        f"{prefix}_BASE": [key],
        f"{prefix}_APT": [{**key, "ARPT_ID": "KAAA"}],
        f"{prefix}_RTE": [
            {**key, "BODY_SEQ": "1", "POINT_SEQ": "20", "POINT": "SECOND"},
            {**key, "BODY_SEQ": "1", "POINT_SEQ": "10", "POINT": "FIRST"},
            {
                **key,
                "ARTCC": "ZBB",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "OTHER",
            },
        ],
    }

    def query(table, *, filters, page_size, cursor):
        return SimpleNamespace(
            rows=[
                row
                for row in tables[table]
                if all(
                    row.get(predicate.field, "") == predicate.value
                    for predicate in filters
                )
            ],
            next_cursor=None,
        )

    (result,) = lookup(query, "test5")
    assert lookup(query, computer_code) == [result]
    assert result["airports"][0]["ARPT_ID"] == "KAAA"
    assert [row["POINT"] for row in result["points"]] == ["FIRST", "SECOND"]


def test_procedure_lookup_without_source_tables_is_not_found():
    def query(*args, **kwargs):
        raise QueryTableNotFoundError("missing")

    with pytest.raises(lookups.NotFoundError):
        lookups.arrivals(query, "TEST")


def test_plot_data_preserves_each_branch_and_unresolved_waypoints():
    def locate(name, point_type):
        assert point_type == "WP"
        if name == "MISSING":
            raise RecordNotFoundError(entity_type="waypoint", identifier=name)
        return {"SHARED": (1, 2), "LEFT": (3, 4), "RIGHT": (5, 6)}[name]

    def row(branch, sequence, point):
        return {
            "ROUTE_PORTION_TYPE": "BODY",
            "ROUTE_NAME": branch,
            "BODY_SEQ": "1",
            "POINT_SEQ": sequence,
            "POINT": point,
            "POINT_TYPE": "WP",
        }

    first, second = lookups.procedure_branches(
        [
            row("A", "10", "SHARED"),
            row("B", "10", "SHARED"),
            row("A", "20", "MISSING"),
            row("B", "20", "RIGHT"),
            row("A", "30", "LEFT"),
        ],
        locate,
    )
    assert [point["name"] for point in first["waypoints"]] == [
        "SHARED",
        "MISSING",
        "LEFT",
    ]
    assert first["waypoints"][1]["position"] is None
    assert "MISSING" in first["waypoints"][1]["issue"]
    assert [point["name"] for point in second["waypoints"]] == ["SHARED", "RIGHT"]
    assert second["waypoints"][-1]["position"] == {"lat": 5, "lon": 6}
