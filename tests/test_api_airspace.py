"""Point-in-region lookups from the FAA boundary tables."""

import pandas as pd
import pytest

from openNASR_api.airspace import AirspaceIndex


def _square(location, altitude, kind, west, south, east, north):
    corners = [
        (west, south),
        (east, south),
        (east, north),
        (west, north),
        (west, south),
    ]
    return [
        {
            "LOCATION_ID": location,
            "ALTITUDE": altitude,
            "TYPE": kind,
            "POINT_SEQ": str((n + 1) * 10),
            "LAT_DECIMAL": str(lat),
            "LONG_DECIMAL": str(lon),
        }
        for n, (lon, lat) in enumerate(corners)
    ]


@pytest.fixture
def index():
    base = pd.DataFrame(
        [
            {"LOCATION_ID": "ZAA", "LOCATION_NAME": "ALPHA"},
            {"LOCATION_ID": "ZBB", "LOCATION_NAME": "BRAVO OCEANIC"},
            {"LOCATION_ID": "ZPP", "LOCATION_NAME": "PACIFIC"},
        ]
    )
    rows = (
        _square("ZAA", "LOW", "ARTCC", -110, 30, -100, 40)
        + _square("ZAA", "HIGH", "ARTCC", -108, 31, -102, 39)
        + _square("ZBB", "UNLIMITED", "FIR", -100, 30, -90, 40)
        + _square("ZBB", "UNLIMITED", "CTA", -100, 30, -95, 40)
        # a region crossing the antimeridian: 170E to 170W (-170)
        + [
            {"LOCATION_ID": "ZPP", "ALTITUDE": "UNLIMITED", "TYPE": "FIR",
             "POINT_SEQ": str((n + 1) * 10), "LAT_DECIMAL": str(lat),
             "LONG_DECIMAL": str(lon)}
            for n, (lon, lat) in enumerate(
                [(170, 10), (180, 10), (-170, 10), (-170, 20),
                 (180, 20), (170, 20), (170, 10)]
            )
        ]
    )  # fmt: skip
    return AirspaceIndex(base, pd.DataFrame(rows))


def _ids(index, lat, lon):
    return [(r.id, r.kind, r.level) for r in index.at(lat, lon)]


def test_a_point_reports_every_region_that_contains_it(index):
    assert _ids(index, 35, -105) == [("ZAA", "ARTCC", "high"), ("ZAA", "ARTCC", "low")]
    assert _ids(index, 30.5, -109) == [("ZAA", "ARTCC", "low")]  # outside the high box
    assert _ids(index, 35, -97) == [
        ("ZBB", "CTA", "unlimited"),
        ("ZBB", "FIR", "unlimited"),
    ]
    assert _ids(index, 35, -92) == [("ZBB", "FIR", "unlimited")]
    assert _ids(index, 0, 0) == []


def test_regions_carry_names_and_a_point_on_the_edge_counts_as_inside(index):
    region = index.at(35, -110)[0]  # exactly on ZAA's western edge
    assert (region.id, region.name) == ("ZAA", "ALPHA")


def test_a_region_crossing_the_antimeridian_works_on_both_sides(index):
    assert _ids(index, 15, 175) == [("ZPP", "FIR", "unlimited")]
    assert _ids(index, 15, -175) == [("ZPP", "FIR", "unlimited")]
    assert _ids(index, 15, 160) == []
    assert _ids(index, 15, -160) == []


def test_unusable_boundaries_are_skipped_not_fatal():
    base = pd.DataFrame([{"LOCATION_ID": "ZXX", "LOCATION_NAME": "X"}])
    rows = pd.DataFrame(
        [
            {"LOCATION_ID": "ZXX", "ALTITUDE": "LOW", "TYPE": "ARTCC",
             "POINT_SEQ": "10", "LAT_DECIMAL": "", "LONG_DECIMAL": "bad"},
        ]
    )  # fmt: skip

    assert len(AirspaceIndex(base, rows)) == 0
    assert AirspaceIndex(base, rows).at(1, 1) == []
