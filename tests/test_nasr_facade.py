import pandas as pd

from openNASR.records import AirportRecord, FaaRecord
from openNASR.repository import AirportRepository, RecordRepository


def test_airport_repository_get_and_singular_facade_are_equivalent(fixture_nasr):
    nasr, _ = fixture_nasr

    from_repository = nasr.airports.get("kbwi")
    from_singular_method = nasr.airport("KBWI")

    assert isinstance(from_repository, FaaRecord)
    assert from_repository["ARPT_ID"] == from_singular_method["ARPT_ID"] == "BWI"
    assert from_repository["ICAO_ID"] == from_singular_method["ICAO_ID"] == "KBWI"


def test_airport_repository_resolves_faa_and_icao_identifiers_case_insensitively(
    fixture_nasr,
):
    nasr, _ = fixture_nasr

    from_faa = nasr.airports.get(" bwi ")
    from_icao = nasr.airports.get(" kbwi ")

    assert from_faa["ARPT_ID"] == from_icao["ARPT_ID"] == "BWI"


def test_airport_record_exposes_typed_nullable_properties():
    airport = AirportRecord(
        {
            "ARPT_ID": "BWI",
            "ICAO_ID": "KBWI",
            "ARPT_NAME": "Baltimore/Washington International",
            "LAT_DECIMAL": "39.1754",
            "LONG_DECIMAL": "-76.6684",
            "ELEV": "146",
        }
    )

    assert airport.faa_id == "BWI"
    assert airport.icao_id == "KBWI"
    assert airport.name == "Baltimore/Washington International"
    assert airport.latitude == 39.1754
    assert airport.longitude == -76.6684
    assert airport.elevation_ft == 146.0
    assert AirportRecord({"ARPT_ID": ""}).faa_id is None


def test_airport_record_exposes_immutable_typed_runway_collections(fixture_nasr):
    nasr, _ = fixture_nasr

    airport = nasr.airports.get("BWI")

    assert isinstance(airport.runways, tuple)
    assert isinstance(airport.runway_ends, tuple)
    assert airport.runways[0]["RWY_ID"] == "10/28"
    assert airport.runway_ends[0]["RWY_END_ID"] == 10


def test_airport_record_associates_optional_ils_component_collections(fixture_nasr):
    nasr, _ = fixture_nasr

    airport = nasr.airports.get("BWI")

    assert airport.ils[0]["ARPT_ID"] == "BWI"
    assert airport.dmes[0]["ARPT_ID"] == "BWI"
    assert airport.glide_slopes[0]["ARPT_ID"] == "BWI"
    assert airport.markers[0]["ARPT_ID"] == "BWI"

    reduced = AirportRepository({"APT_BASE": nasr["APT_BASE"]})
    assert reduced.get("BWI").ils == ()


def test_record_repository_normalizes_composite_keys_and_optional_filters():
    repository = RecordRepository(
        pd.DataFrame(
            [
                {"CENTER": "ZOB", "ALTITUDE": "HIGH", "STATE": "OH"},
                {"CENTER": "ZOB", "ALTITUDE": "LOW", "STATE": "OH"},
                {"CENTER": "ZNY", "ALTITUDE": "HIGH", "STATE": "NY"},
            ]
        ),
        entity_type="ARTCC boundary",
        identifier_columns=("CENTER", "ALTITUDE"),
    )

    record = repository.get((" zob ", " high "), STATE=" oh ")

    assert record["CENTER"] == "ZOB"
    assert record["ALTITUDE"] == "HIGH"
    assert repository.find(("ZOB", "HIGH"), STATE=None) == (record,)
