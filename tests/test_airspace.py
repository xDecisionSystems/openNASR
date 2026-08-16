"""ARTCC access uses the deterministic core fixture."""

from openNASR.arb import Boundary
from shapely.geometry import MultiPolygon, Polygon


def test_load_artcc_and_access_high_boundary(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    nasr.loadARTCC()
    zob = nasr.artcc.getARTCC("ZOB")

    assert zob is not None
    assert zob.boundaries["high"] is zob.high
    assert zob.boundaries["low"] is zob.low
    assert zob.high.getShape.is_valid
    assert zob.low.getShape.is_valid


def test_boundary_preserves_disjoint_closed_rings_as_a_multipolygon():
    boundary = Boundary(
        [0, 1, 1, 0, 0, 3, 4, 4, 3, 3],
        [0, 0, 1, 1, 0, 0, 0, 1, 1, 0],
    )

    assert isinstance(boundary.getShape, MultiPolygon)
    assert len(boundary.getShape.geoms) == 2
    assert boundary.bbox == (0.0, 0.0, 4.0, 1.0)


def test_boundary_uses_a_polygon_for_a_single_ring():
    boundary = Boundary([0, 1, 1, 0, 0], [0, 0, 1, 1, 0])

    assert isinstance(boundary.getShape, Polygon)
