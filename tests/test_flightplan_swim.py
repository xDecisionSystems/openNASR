"""FAA SWIM (ERAM) route text: ``./.`` separators, slashed lat/lon points and
fix-radial-distance waypoints, as published in SFDPS flight plan messages."""

import math

import pandas as pd
import pytest

from openNASR.flightplan import RouteResolver


@pytest.fixture
def tables():
    return {
        "APT_BASE": pd.DataFrame(
            [
                {
                    "ARPT_ID": "ORD",
                    "ICAO_ID": "KORD",
                    "LAT_DECIMAL": "41.98",
                    "LONG_DECIMAL": "-87.90",
                    "MAG_VARN": "3",
                    "MAG_HEMIS": "W",
                },
                {
                    "ARPT_ID": "SDF",
                    "ICAO_ID": "KSDF",
                    "LAT_DECIMAL": "38.17",
                    "LONG_DECIMAL": "-85.74",
                    "MAG_VARN": "4",
                    "MAG_HEMIS": "W",
                },
                {
                    "ARPT_ID": "HUM",
                    "ICAO_ID": "KHUM",
                    "LAT_DECIMAL": "29.57",
                    "LONG_DECIMAL": "-90.66",
                    "MAG_VARN": "1",
                    "MAG_HEMIS": "W",
                },
            ]
        ),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "SEWTO", "LAT_DECIMAL": "40.80", "LONG_DECIMAL": "-86.70"},
                {"FIX_ID": "LLACH", "LAT_DECIMAL": "28.50", "LONG_DECIMAL": "-91.20"},
                {"FIX_ID": "BAIRN", "LAT_DECIMAL": "28.00", "LONG_DECIMAL": "-81.00"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(
            [
                # A VOR with 10 degrees of west variation: radial 090 (magnetic)
                # points to 080 true.
                {
                    "NAV_ID": "OBK",
                    "NAV_TYPE": "VOR/DME",
                    "LAT_DECIMAL": "42.00",
                    "LONG_DECIMAL": "-87.80",
                    "MAG_VARN": "10",
                    "MAG_VARN_HEMIS": "W",
                },
            ]
        ),
    }


def _distance_nm(a, b):
    phi1, phi2 = math.radians(a[0]), math.radians(b[0])
    d = math.acos(
        min(
            1.0,
            math.sin(phi1) * math.sin(phi2)
            + math.cos(phi1) * math.cos(phi2) * math.cos(math.radians(b[1] - a[1])),
        )
    )
    return d * 6371008.8 / 1852


def _bearing(a, b):
    phi1, phi2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def test_eram_separator_keeps_the_rest_of_the_route(tables):
    result = RouteResolver(tables).resolve("KORD./.SEWTO..KSDF/2218")

    assert result.complete, result.diagnostics
    assert [p.name for p in result.waypoints] == ["KORD", "SEWTO", "KSDF"]
    # Only the /2218 time group is reported as ignored, at its filed position.
    ignored = [d for d in result.diagnostics if d.code == "ignored_speed_level"]
    assert [(d.token, d.position) for d in ignored] == [("2218", 19)]


def test_fix_radial_distance_uses_magnetic_variation(tables):
    result = RouteResolver(tables).resolve("KORD./.OBK090020..SEWTO..KSDF/2218")

    assert result.complete, result.diagnostics
    names = [p.name for p in result.waypoints]
    assert names == ["KORD", "OBK090020", "SEWTO", "KSDF"]
    frd = result.waypoints[1]
    assert frd.kind == "radial_distance"
    base = (42.00, -87.80)
    assert _distance_nm(base, (frd.lat, frd.lon)) == pytest.approx(20.0, abs=0.05)
    # 090 magnetic with 10 degrees west variation is 080 true.
    assert _bearing(base, (frd.lat, frd.lon)) == pytest.approx(80.0, abs=0.2)


def test_fix_radial_distance_on_a_fix_uses_nearest_variation(tables):
    # BAIRN is a fix, so the variation comes from the nearest navaid or
    # airport on record: KHUM (1 W) here, so 170 magnetic is 169 true.
    result = RouteResolver(tables).resolve("KHUM./.BAIRN170010..KHUM")
    assert result.complete, result.diagnostics
    frd = result.waypoints[1]
    assert _bearing((28.00, -81.00), (frd.lat, frd.lon)) == pytest.approx(
        169.0, abs=0.2
    )
    assert _distance_nm((28.00, -81.00), (frd.lat, frd.lon)) == pytest.approx(
        10.0, abs=0.05
    )


def test_slashed_latlon_point(tables):
    result = RouteResolver(tables).resolve("2706N/09216W..LLACH..KHUM/2158")

    assert result.complete, result.diagnostics
    first = result.waypoints[0]
    assert first.kind == "latlon"
    assert (first.lat, first.lon) == pytest.approx((27.1, -92.2667), abs=1e-3)
    assert [p.name for p in result.waypoints][1:] == ["LLACH", "KHUM"]


def test_unknown_radial_distance_base_is_still_an_unknown_waypoint(tables):
    result = RouteResolver(tables).resolve("KORD..ZZZ090020..KSDF")
    assert not result.complete
    assert result.diagnostics[-1].code == "RecordNotFoundError"
    assert result.diagnostics[-1].token == "ZZZ090020"


@pytest.fixture
def star_tables(tables):
    """A STAR like OZZZI.OZZZI2: transition FLASK -> MIDDL -> SCHUL -> OZZZI,
    body OZZZI -> HAARY -> KATL."""

    fixes = [
        ("FLASK", "35.5", "-82.0"),
        ("MIDDL", "34.9", "-83.0"),
        ("SCHUL", "34.4", "-83.6"),
        ("OZZZI", "34.0", "-84.0"),
        ("HAARY", "33.8", "-84.2"),
    ]
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": f, "LAT_DECIMAL": a, "LONG_DECIMAL": o}
                    for f, a, o in fixes
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["APT_BASE"] = pd.concat(
        [
            tables["APT_BASE"],
            pd.DataFrame(
                [
                    {
                        "ARPT_ID": "ATL",
                        "ICAO_ID": "KATL",
                        "LAT_DECIMAL": "33.64",
                        "LONG_DECIMAL": "-84.43",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    code = "OZZZI.OZZZI2"

    def row(portion, transition, seq, point):
        return {
            "STAR_COMPUTER_CODE": code,
            "ARTCC": "ZTL",
            "ROUTE_PORTION_TYPE": portion,
            "TRANSITION_COMPUTER_CODE": transition,
            "BODY_SEQ": "1",
            "POINT_SEQ": str(seq),
            "POINT": point,
        }

    tables["STAR_BASE"] = pd.DataFrame([{"STAR_COMPUTER_CODE": code, "ARTCC": "ZTL"}])
    tables["STAR_RTE"] = pd.DataFrame(
        [
            row("TRANSITION", "FLASK.OZZZI2", 10, "FLASK"),
            row("TRANSITION", "FLASK.OZZZI2", 20, "MIDDL"),
            row("TRANSITION", "FLASK.OZZZI2", 30, "SCHUL"),
            row("TRANSITION", "FLASK.OZZZI2", 40, "OZZZI"),
            row("BODY", "", 10, "OZZZI"),
            row("BODY", "", 20, "HAARY"),
            row("BODY", "", 30, "KATL"),
        ]
    )
    for table in ("DP_BASE", "DP_RTE"):
        tables[table] = pd.DataFrame(
            columns=["DP_NAME", "ARTCC", "DP_COMPUTER_CODE", "TRANSITION_COMPUTER_CODE"]
        )
    return tables


def test_star_joined_inside_a_transition(star_tables):
    result = RouteResolver(star_tables).resolve("KORD./.SEWTO..SCHUL.OZZZI2.KATL/2321")

    assert result.complete, result.diagnostics
    assert [p.name for p in result.waypoints] == [
        "KORD",
        "SEWTO",
        "SCHUL",
        "OZZZI",
        "HAARY",
        "KATL",
    ]
    assert {p.via for p in result.waypoints[2:5]} == {"SCHUL.OZZZI2"}


def test_star_joined_on_its_body(star_tables):
    result = RouteResolver(star_tables).resolve("KORD..SEWTO..HAARY.OZZZI2.KATL")

    assert result.complete, result.diagnostics
    assert [p.name for p in result.waypoints] == ["KORD", "SEWTO", "HAARY", "KATL"]


def test_star_by_short_name_after_a_fix_not_on_it(star_tables):
    # ERAM files ``..ROKNN4.CGF`` for the STAR coded ROKNN.ROKNN4; from a fix
    # that is not on it the STAR is flown from its body.
    result = RouteResolver(star_tables).resolve("KORD..SEWTO.OZZZI2.KATL")

    assert result.complete, result.diagnostics
    assert [p.name for p in result.waypoints] == [
        "KORD",
        "SEWTO",
        "OZZZI",
        "HAARY",
        "KATL",
    ]


def test_star_by_short_name_after_a_fix_on_a_transition(star_tables):
    result = RouteResolver(star_tables).resolve("KORD..MIDDL..OZZZI2.KATL")

    assert result.complete, result.diagnostics
    assert [p.name for p in result.waypoints] == [
        "KORD",
        "MIDDL",
        "SCHUL",
        "OZZZI",
        "HAARY",
        "KATL",
    ]


def test_route_stops_before_an_unknown_portion(star_tables):
    # ``DRUGA.XXX..ROKNN4``: where the flight rejoins the arrival is not
    # known, so nothing after the last known point is placed.
    result = RouteResolver(star_tables).resolve("KORD..SEWTO.XXX..OZZZI2.KATL")

    assert not result.complete
    assert [p.name for p in result.waypoints] == ["KORD", "SEWTO"]
    assert [(d.code, d.token, d.position) for d in result.diagnostics] == [
        ("unknown_route_portion", "XXX", 12)
    ]


def test_unknown_identifiers_are_skipped_not_fatal(tables):
    result = RouteResolver(tables).resolve("KORD./.ZWE280024..SEWTO..NOSUCH..KSDF")

    assert not result.complete
    assert [p.name for p in result.waypoints] == ["KORD", "SEWTO", "KSDF"]
    skipped = [(d.code, d.token, d.position, d.detail) for d in result.diagnostics]
    assert skipped == [
        ("RecordNotFoundError", "ZWE280024", 7, {"skipped": True}),
        ("RecordNotFoundError", "NOSUCH", 25, {"skipped": True}),
    ]


def test_an_unknown_identifier_inside_a_longer_one_is_not_rewritten(tables):
    from openNASR._route_resolver import _skip_unknown_identifier

    class Error:
        token = "ZWE"
        position = 0

    assert _skip_unknown_identifier("ZWEX..KSDF", Error()) is None
    assert _skip_unknown_identifier("ZWE..KSDF", Error()) == "~  ..KSDF"


def test_eram_unknown_portion_ends_the_drawn_route(tables):
    result = RouteResolver(tables).resolve("KORD..SEWTO.XXX..KSDF")

    assert not result.complete
    assert [p.name for p in result.waypoints] == ["KORD", "SEWTO"]
    unknown = [d for d in result.diagnostics if d.code == "unknown_route_portion"]
    assert [(d.token, d.position) for d in unknown] == [("XXX", 12)]


def test_a_route_that_starts_with_an_unknown_portion_has_no_points(tables):
    result = RouteResolver(tables).resolve("XXX..KSDF")

    assert result.points == ()
    assert [d.code for d in result.diagnostics] == ["unknown_route_portion"]


def _two_airport_star(star_tables):
    """OZZZI2 with one body for KATL and another for KSDF (as ROKNN4 has one
    body for CGF and five runway-dependent ones for CLE)."""

    def body(name, seq, point):
        return {
            "STAR_COMPUTER_CODE": "OZZZI.OZZZI2",
            "ARTCC": "ZTL",
            "ROUTE_PORTION_TYPE": "BODY",
            "TRANSITION_COMPUTER_CODE": "",
            "ROUTE_NAME": name,
            "BODY_SEQ": "1",
            "POINT_SEQ": str(seq),
            "POINT": point,
        }

    routes = star_tables["STAR_RTE"]
    transitions = routes[routes["ROUTE_PORTION_TYPE"].eq("TRANSITION")].assign(
        ROUTE_NAME="FLASK.OZZZI2"
    )
    star_tables["STAR_RTE"] = pd.concat(
        [
            transitions,
            pd.DataFrame(
                [
                    body("OZZZI-ATL", 10, "OZZZI"),
                    body("OZZZI-ATL", 20, "HAARY"),
                    body("OZZZI-ATL", 30, "KATL"),
                    body("OZZZI-SDF", 10, "OZZZI"),
                    body("OZZZI-SDF", 20, "SEWTO"),
                    body("OZZZI-SDF", 30, "KSDF"),
                ]
            ),
        ],
        ignore_index=True,
    )
    star_tables["STAR_APT"] = pd.DataFrame(
        [
            {
                "STAR_COMPUTER_CODE": "OZZZI.OZZZI2",
                "ARTCC": "ZTL",
                "BODY_NAME": name,
                "ARPT_ID": airport,
            }
            for name, airport in (("OZZZI-ATL", "ATL"), ("OZZZI-SDF", "SDF"))
        ]
    )
    return star_tables


@pytest.mark.parametrize(
    ("route", "expected"),
    [
        (
            "KORD./.SCHUL.OZZZI2.KATL/2321",
            ["KORD", "SCHUL", "OZZZI", "HAARY", "KATL"],
        ),
        ("KORD./.SCHUL.OZZZI2.KSDF", ["KORD", "SCHUL", "OZZZI", "SEWTO", "KSDF"]),
    ],
)
def test_eram_route_uses_the_destinations_star_body(star_tables, route, expected):
    # ``./.`` once hid the destination, so the body was never narrowed to it.
    result = RouteResolver(_two_airport_star(star_tables)).resolve(route)

    assert result.complete, result.diagnostics
    assert [p.name for p in result.waypoints] == expected


def test_many_unknown_identifiers_at_the_end_are_all_skipped(tables):
    # QFA16 (FAA SWIM, 2026-11-25): an oceanic route ending in six names
    # outside NASR. Before 2.1.38 the sixth stopped resolution and the
    # route came back empty.
    route = "KORD..SEWTO..2706N/09216W..MEPEM.Q144.ATROP.H224.TEBOT..YBBN/1349"
    result = RouteResolver(tables).resolve(route)

    assert not result.complete
    assert [p.name for p in result.waypoints] == ["KORD", "SEWTO", "2706N09216W"]
    skipped = [d.token for d in result.diagnostics if d.detail == {"skipped": True}]
    assert skipped == ["MEPEM", "Q144", "ATROP", "H224", "TEBOT", "YBBN"]
