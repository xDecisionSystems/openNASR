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
