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


def test_maa_repository_get_and_singular_facade_are_equivalent(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    from_repository = nasr.maas.get("aoh001")
    from_singular_method = nasr.maa("AOH001")

    assert from_repository.maa_id == from_singular_method.maa_id == "AOH001"


def test_maa_record_exposes_typed_fields_including_type_name(make_nasr_from_fixture):
    """MAA is the FAA's "Miscellaneous Activity Area" family (verified from
    the FAA's own MAA DATA LAYOUT.pdf, PLAN.md Milestone 12 task 12.1) -- not
    military airspace, despite living alongside PJA/MTR."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    maa = nasr.maas.get("AOH001")

    assert maa.record.type_name == "AEROBATIC PRACTICE"
    assert maa.name == "Synthetic Aerobatic Practice Area"
    assert maa.record.state == "OH"
    assert maa.record.airport_ids == ("BKL",)


def test_maa_contacts_are_ordered_by_freq_seq_not_file_order(make_nasr_from_fixture):
    """MAA_CON ordered by (MAA_ID, FREQ_SEQ) per the FAA layout document
    (PLAN.md task 12.2); tests/fixtures/.../MAA_CON.csv lists FREQ_SEQ 2
    before 1 specifically to catch a repository that trusted file order."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    maa = nasr.maas.get("AOH001")

    assert [contact.sequence for contact in maa.contacts] == [1, 2]
    assert maa.contacts[0].commercial_frequency == "121.5"
    assert maa.contacts[1].commercial_frequency == "124.5"


def test_maa_remarks_are_ordered_by_ref_col_seq_no(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    maa = nasr.maas.get("AOH001")

    assert [remark.sequence for remark in maa.remarks] == [1, 2]
    assert maa.remarks[0].remark == "First synthetic remark for fixture testing."


def test_maa_geometry_closes_an_unclosed_source_ring_in_point_seq_order(
    make_nasr_from_fixture,
):
    """MAA_SHP rings are not explicitly closed in real FAA source data
    (verified against the real 2024-06-13 archive, PLAN.md task 12.2), unlike
    ARB_SEG; tests/fixtures/.../MAA_SHP.csv lists POINT_SEQ out of file order
    to also confirm points are sorted by sequence, not file order."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    maa = nasr.maas.get("AOH001")

    assert [point.sequence for point in maa.shape_points] == [1, 2, 3, 4]
    geometry = maa.geometry
    assert geometry is not None
    assert geometry.is_valid
    assert geometry.equals(
        Polygon(
            [
                (-82.0, 40.5),
                (-81.98333333333333, 40.5),
                (-81.98333333333333, 40.516666666666666),
                (-82.0, 40.516666666666666),
                (-82.0, 40.5),
            ]
        )
    )


def test_maa_geometry_is_none_when_no_shape_points_exist(make_nasr_from_fixture):
    """Some MAA_BASE rows describe only a center point and radius, with no
    matching MAA_SHP rows (verified from the real archive, task 12.2)."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    maa = nasr.maas.get("AOH001")
    # Remove the shape points to simulate a radius-only area.
    maa = maa.__class__(
        maa.record, contacts=maa.contacts, remarks=maa.remarks, shape_points=()
    )

    assert maa.geometry is None


def test_maa_repository_raises_record_not_found_for_an_unmatched_identifier(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    with pytest.raises(RecordNotFoundError):
        nasr.maas.get("does-not-exist")


def test_parachute_jump_area_repository_and_singular_facade_are_equivalent(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    from_repository = nasr.parachute_jump_areas.get("pmd001")
    from_singular_method = nasr.parachute_jump_area("PMD001")

    assert from_repository.pja_id == from_singular_method.pja_id == "PMD001"


def test_parachute_jump_area_record_exposes_typed_fields(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    area = nasr.parachute_jump_areas.get("PMD001")

    assert area.drop_zone_name == "Synthetic Drop Zone"
    assert area.record.state == "MD"
    assert area.record.radius == "1.0"
    assert area.record.airport_site_key == ("00000001A", "A")


def test_parachute_jump_area_links_its_airport_when_a_site_key_is_present(
    make_nasr_from_fixture,
):
    """PJA_BASE.SITE_NO is populated on roughly two thirds of rows in the
    real FAA archive, not every row (verified in task 12.2); the airport
    link must be optional, not required."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    linked = nasr.parachute_jump_areas.get("PMD001")
    unlinked = nasr.parachute_jump_areas.get("PMD002")

    assert linked.airport is not None
    assert linked.airport.raw["ARPT_ID"] == "BWI"
    assert unlinked.record.airport_site_key is None
    assert unlinked.airport is None


def test_parachute_jump_area_contacts_are_ordered_by_pja_id_then_fac_name(
    make_nasr_from_fixture,
):
    """PJA_CON is ordered by (PJA_ID, FAC_NAME) -- a name-based key, not a
    numeric sequence (verified in task 12.2); the fixture lists "BALTIMORE
    TOWER" after "WASHINGTON APPROACH" in file order specifically to catch a
    repository that trusted file order instead of sorting by FAC_NAME."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    area = nasr.parachute_jump_areas.get("PMD001")

    assert [contact.facility_name for contact in area.contacts] == [
        "BALTIMORE TOWER",
        "WASHINGTON APPROACH",
    ]


def test_parachute_jump_area_repository_raises_record_not_found_for_an_unmatched(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    with pytest.raises(RecordNotFoundError):
        nasr.parachute_jump_areas.get("does-not-exist")
