"""Airport construction and collection access use deterministic fixtures only."""

from openNASR import Airport


def test_construct_airport_by_faa_identifier(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    airport = Airport("BWI", nasr)

    assert airport.faa_id == "BWI"
    assert airport.icao_id == "KBWI"


def test_construct_airport_by_icao_identifier(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    airport = Airport("KBWI", nasr)

    assert airport.faa_id == "BWI"


def test_airport_collections_are_available_without_plotting(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    airport = Airport("BWI", nasr)

    assert airport.rwy.ids == ["10/28"]
    assert set(airport.rwyend.ids) == {"10", "28"}
    assert airport.ils.ids == ["10"]
