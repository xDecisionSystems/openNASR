"""Point-in-region lookups from the FAA boundary tables."""

import pandas as pd
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box

from openNASR_api.airspace import AirspaceIndex, Region
from openNASR_api.map_layers import MapLayer


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


def test_artcc_map_includes_only_matching_outlines_and_clips_layers(index):
    outlines = index.artcc_boundaries(35, -105)
    assert {(boundary["id"], boundary["level"]) for boundary in outlines} == {
        ("ZAA", "high"),
        ("ZAA", "low"),
    }
    for boundary in outlines:
        (ring,) = boundary["rings"]
        assert len(ring) == 5 and ring[0] == ring[-1]
    assert index.artcc_boundaries(35, -97) == []

    layer = MapLayer(
        [
            ("IN", Point(-105, 35)),
            ("OUT", Point(-95, 35)),
            ("", LineString([(-115, 35), (-95, 35)])),
        ]
    )
    features = layer.within(index.artcc_extent(35, -105))
    assert features["points"] == [{"name": "IN", "lat": 35, "lon": -105}]
    (line,) = features["lines"]
    assert [point["lon"] for point in line] == [-110, -100]


def test_artcc_layer_handles_airports_on_both_sides_of_the_dateline():
    base = pd.DataFrame([{"LOCATION_ID": "ZXX"}])
    segments = pd.DataFrame(_square("ZXX", "HIGH", "ARTCC", 170, 10, -170, 20))
    index = AirspaceIndex(base, segments)
    layer = MapLayer(
        [
            ("EAST", Point(175, 15)),
            ("WEST", Point(-175, 15)),
            ("OUT", Point(165, 15)),
        ]
    )
    for longitude in (175, -175):
        (boundary,) = index.artcc_boundaries(15, longitude)
        assert boundary["id"] == "ZXX"
        assert {
            p["name"] for p in layer.within(index.artcc_extent(15, longitude))["points"]
        } == {
            "EAST",
            "WEST",
        }


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


def test_class_multipolygon_crosses_the_dateline_without_losing_other_parts(
    tmp_path, monkeypatch
):
    region = Region("TEST", "Test", "CLASS", "", airspace_class="E")
    outline = MultiPolygon(
        [
            Polygon([(170, 10), (-170, 10), (-170, 20), (170, 20)]),
            box(-102, 30, -100, 32),
        ]
    )
    monkeypatch.setattr(
        "openNASR_api.airspace._class_regions", lambda path: [(region, outline)]
    )
    base = pd.DataFrame(columns=["LOCATION_ID"])
    segments = pd.DataFrame(columns=["POINT_SEQ", "LOCATION_ID", "ALTITUDE", "TYPE"])
    class_index = AirspaceIndex(base, segments, tmp_path / "class_airspace.parquet")

    assert class_index.at(15, 175) == class_index.at(15, -175) == [region]
    assert class_index.at(31, -101) == [region]
    assert class_index.at(15, 0) == []


def test_viewport_clips_outlines_without_drawing_viewport_edges(index):
    (boundary,) = index.boundaries_in_view(-111, 34, 2, 36)
    assert boundary["kind"] == "ARTCC"
    (line,) = boundary["rings"]
    assert {(p["lon"], p["lat"]) for p in line} == {(-110, 34), (-110, 36)}
    assert index.boundaries_in_view(-107, 34, 2, 36) == []


def test_viewport_follows_boundary_across_antimeridian(index):
    (boundary,) = index.boundaries_in_view(175, 9, 10, 11)
    assert boundary["id"] == "ZPP"
    (line,) = boundary["rings"]
    assert {(p["lon"], p["lat"]) for p in line} == {(175, 10), (-180, 10), (-175, 10)}
