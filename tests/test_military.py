"""Military training route access uses the deterministic core fixture."""

import pytest

from openNASR.exceptions import RecordNotFoundError


def test_military_training_route_repository_and_singular_facade_are_equivalent(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    from_repository = nasr.military_training_routes.get(("ir", "999"))
    from_singular_method = nasr.military_training_route(("IR", "999"))

    assert from_repository.route_key == from_singular_method.route_key == ("IR", "999")
    assert len(nasr.military_training_routes._indexes) == 12


def test_military_training_route_artccs_is_parsed_from_a_space_separated_list(
    make_nasr_from_fixture,
):
    """ARTCC is common to every MTR_* file per the FAA layout document, but it
    is a space-separated list of idents the route traverses, not part of the
    identity key (verified against the real archive, PLAN.md task 12.2)."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    route = nasr.military_training_routes.get(("IR", "999"))

    assert route.record.artccs == ("ZID", "ZTL")
    assert route.record.flight_service_stations == ("SDF",)


def test_military_training_route_agencies_are_ordered_by_agency_type(
    make_nasr_from_fixture,
):
    """tests/fixtures/.../MTR_AGY.csv lists AGENCY_TYPE "S1" before "O" in
    file order specifically to catch a repository that trusted file order."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    route = nasr.military_training_routes.get(("IR", "999"))

    assert [agency.agency_type for agency in route.agencies] == ["O", "S1"]


def test_military_training_route_points_are_ordered_by_route_pt_seq(
    make_nasr_from_fixture,
):
    """The FAA's own MTR DATA LAYOUT.pdf documents MTR_PT as ordered by
    ROUTE_PT_SEQ but keyed by ROUTE_PT_ID -- the two disagree in this
    fixture (ROUTE_PT_ID "Z" then "A" in file order, ROUTE_PT_SEQ 20 then 10)
    specifically to prove display order follows ROUTE_PT_SEQ, not
    ROUTE_PT_ID and not file order (PLAN.md task 12.2)."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    route = nasr.military_training_routes.get(("IR", "999"))

    assert [point.sequence for point in route.points] == [10, 20]
    assert [point.identifier for point in route.points] == ["A", "Z"]
    assert route.points[0].next_point_id == "Z"
    assert route.points[1].next_point_id == "A"


def test_military_training_route_procedures_terrain_and_widths_are_ordered(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    route = nasr.military_training_routes.get(("IR", "999"))

    assert [procedure.sequence for procedure in route.procedures] == [1, 2]
    assert route.procedures[0].text == "FIRST SYNTHETIC PROCEDURE."
    assert [item.sequence for item in route.terrain] == [1]
    assert [item.sequence for item in route.widths] == [1]


def test_military_training_route_repository_raises_record_not_found(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    with pytest.raises(RecordNotFoundError):
        nasr.military_training_routes.get(("IR", "does-not-exist"))


def test_military_training_route_identifier_requires_a_two_part_tuple(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    with pytest.raises(ValueError):
        nasr.military_training_routes.get("IR")
