"""ARTCC access uses the deterministic core fixture."""

import pytest

from openNASR.arb import ARB, Boundary
from openNASR.coordinates import ll2xy
from openNASR.cfcn import ll2xy as legacy_ll2xy
from openNASR.exceptions import RecordNotFoundError
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


def test_boundary_point_order_matches_the_source_arb_seg_row_order(
    make_nasr_from_fixture,
):
    """ARB_SEG rows are consumed in file order, not resorted -- Boundary's
    ring-closure detection depends on encountering each ring's points in
    source order, so silently reordering them (e.g. by coordinate) would
    produce wrong or invalid polygons without necessarily failing
    ``is_valid``."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    nasr.loadARTCC()
    zob = nasr.artcc.getARTCC("ZOB")

    # tests/fixtures/core/pre_2026_09/CSV_Data/pre_2026_09/ARB_SEG.csv lists
    # the HIGH boundary's five rows, in file order, tracing this rectangle.
    assert zob.high.lonlat == [
        (-82.2, 40.8),
        (-81.8, 40.8),
        (-81.8, 41.2),
        (-82.2, 41.2),
        (-82.2, 40.8),
    ]


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
    assert boundary.latlon[1] == (0.0, 1.0)
    assert boundary.lonlat[1] == (1.0, 0.0)


def test_coordinates_module_preserves_cfcn_compatibility():
    assert ll2xy is legacy_ll2xy


def test_artcc_repository_get_and_singular_facade_are_equivalent(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    from_repository = nasr.artccs.get("zob")
    from_singular_method = nasr.artcc("ZOB")

    assert from_repository.location_id == from_singular_method.location_id == "ZOB"
    assert from_repository.boundaries["high"] is from_repository.high
    assert from_repository.boundaries["low"] is from_repository.low


def test_artcc_facade_boundary_matches_the_legacy_arb_geometry(
    make_nasr_from_fixture,
):
    """The new facade must wrap the same, already-verified Boundary geometry
    the legacy ARB/ARTCC path already produces for the same cycle, not a
    reimplementation."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    modern = nasr.artccs.get("ZOB")
    legacy = ARB(nasr).getARTCC("ZOB")

    assert modern.high.bbox == legacy.high.bbox
    assert modern.high.lonlat == legacy.high.lonlat
    assert modern.high.getShape.equals(legacy.high.getShape)
    assert modern.low.bbox == legacy.low.bbox
    assert modern.low.lonlat == legacy.low.lonlat
    assert modern.low.getShape.equals(legacy.low.getShape)


def test_artcc_repository_raises_record_not_found_for_an_unmatched_identifier(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    with pytest.raises(RecordNotFoundError):
        nasr.artccs.get("does-not-exist")


def test_legacy_load_artcc_still_works_alongside_the_modern_facade(
    make_nasr_from_fixture,
):
    """``nasr.loadARTCC()`` (legacy) and ``nasr.artccs``/``nasr.artcc()``
    (modern) are independent entry points that coexist. Note:
    ``loadARTCC()`` assigns the *instance attribute* ``nasr.artcc`` (an
    ``ARB`` object), which shadows the ``NASR.artcc()`` *method* of the same
    name once called -- this is why the modern facade's own regression tests
    above call ``nasr.artcc(...)`` without ever calling ``loadARTCC()`` in
    the same instance."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    nasr.loadARTCC()

    assert nasr.artcc.getARTCC("ZOB").high.getShape.is_valid
    # The plural repository is unaffected by the legacy singular attribute.
    assert nasr.artccs.get("ZOB").high.getShape.is_valid
