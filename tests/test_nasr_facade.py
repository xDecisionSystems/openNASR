import pandas as pd
import pytest

from openNASR.exceptions import AmbiguousRecordError, SchemaMismatchError
from openNASR.records import AirportRecord, FaaRecord
from openNASR.repository import (
    AirportRepository,
    FixRepository,
    NavaidRepository,
    RecordRepository,
)


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
            "UNMODELED_FAA_FIELD": "preserved verbatim",
        }
    )

    assert airport.faa_id == "BWI"
    assert airport.icao_id == "KBWI"
    assert airport.name == "Baltimore/Washington International"
    assert airport.latitude == 39.1754
    assert airport.longitude == -76.6684
    assert airport.elevation_ft == 146.0
    assert airport.raw["UNMODELED_FAA_FIELD"] == "preserved verbatim"
    assert AirportRecord({"ARPT_ID": ""}).faa_id is None


def test_airport_record_exposes_immutable_typed_runway_collections(fixture_nasr):
    nasr, _ = fixture_nasr

    airport = nasr.airports.get("BWI")

    assert isinstance(airport.runways, tuple)
    assert isinstance(airport.runway_ends, tuple)
    assert airport.runways[0]["RWY_ID"] == "10/28"
    assert airport.runway_ends[0]["RWY_END_ID"] == 10


def test_airport_repository_rejects_missing_reciprocal_runway_end(fixture_nasr):
    nasr, _ = fixture_nasr
    incomplete = dict(nasr)
    incomplete["APT_RWY_END"] = nasr["APT_RWY_END"].iloc[:1]

    with pytest.raises(SchemaMismatchError, match="reciprocal runway-end"):
        AirportRepository(incomplete).get("BWI")


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


def test_fix_repository_exposes_typed_source_fields(fixture_nasr):
    nasr, _ = fixture_nasr

    fix = nasr.fix("aabee")

    assert fix.identifier == "AABEE"
    assert fix.latitude == 39.0
    assert fix.longitude == -76.0
    assert fix.state is None
    assert fix.country is None
    assert fix.high_artcc is None
    assert fix.low_artcc is None


def test_fix_repository_raises_for_duplicate_identifiers():
    repository = FixRepository(
        {"FIX_BASE": pd.DataFrame([{"FIX_ID": "DUP"}, {"FIX_ID": "DUP"}])}
    )

    with pytest.raises(AmbiguousRecordError):
        repository.get("dup")


def test_navaid_filters_are_optional_and_conjunctive(capsys):
    repository = NavaidRepository(
        {
            "NAV_BASE": pd.DataFrame(
                [
                    {
                        "NAV_ID": "DUP",
                        "STATE_CODE": "OH",
                        "COUNTRY_CODE": "US",
                        "NAV_TYPE": "VOR",
                        "HIGH_ALT_ARTCC_ID": "ZOB",
                        "LOW_ALT_ARTCC_ID": "ZOB",
                    },
                    {
                        "NAV_ID": "DUP",
                        "STATE_CODE": "NY",
                        "COUNTRY_CODE": "US",
                        "NAV_TYPE": "VOR",
                        "HIGH_ALT_ARTCC_ID": "ZNY",
                        "LOW_ALT_ARTCC_ID": "ZNY",
                    },
                ]
            )
        }
    )

    assert len(repository.find("dup")) == 2
    assert repository.get("dup", state=" oh ", artcc="zob")["STATE_CODE"] == "OH"
    with pytest.raises(AmbiguousRecordError) as raised:
        repository.get("dup")
    assert len(raised.value.candidates) == 2
    assert capsys.readouterr().out == ""


def test_navaid_repository_supports_navtype_compatibility_alias():
    repository = NavaidRepository(
        {
            "NAV_BASE": pd.DataFrame(
                [
                    {
                        "NAV_ID": "ABC",
                        "NAV_TYPE": "VOR",
                        "STATE_CODE": "OH",
                        "COUNTRY_CODE": "US",
                        "HIGH_ALT_ARTCC_ID": "ZOB",
                        "LOW_ALT_ARTCC_ID": "ZOB",
                    }
                ]
            )
        }
    )

    assert repository.get("ABC", navType="vor")["NAV_ID"] == "ABC"
    with pytest.raises(ValueError, match="must agree"):
        repository.find("ABC", nav_type="VOR", navType="NDB")
