import inspect

import pandas as pd
import pytest
from numpy import ndarray

from openNASR.exceptions import AmbiguousRecordError, SchemaMismatchError
from openNASR.fix import FixRecord
from openNASR.ils import DmeRecord, GlideSlopeRecord, IlsRecord, MarkerRecord
from openNASR.nav import NavaidRecord
from openNASR.records import (
    AirportRecord,
    DmeRecord as LegacyDmeRecord,
    FaaRecord,
    GlideSlopeRecord as LegacyGlideSlopeRecord,
    IlsRecord as LegacyIlsRecord,
    MarkerRecord as LegacyMarkerRecord,
    RunwayEndRecord as LegacyRunwayEndRecord,
    RunwayRecord as LegacyRunwayRecord,
)
from openNASR.repository import (
    AirportRepository,
    FixRepository,
    NavaidRepository,
    RecordRepository,
)
from openNASR.rwy import RunwayEndRecord, RunwayRecord


def test_runway_and_ils_record_types_use_domain_owned_compatibility_exports():
    assert LegacyRunwayRecord is RunwayRecord
    assert LegacyRunwayEndRecord is RunwayEndRecord
    assert LegacyIlsRecord is IlsRecord
    assert LegacyDmeRecord is DmeRecord
    assert LegacyGlideSlopeRecord is GlideSlopeRecord
    assert LegacyMarkerRecord is MarkerRecord


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


def test_location_record_strings_include_type_name_and_coordinates():
    airport = AirportRecord(
        {
            "ARPT_NAME": "Baltimore/Washington International",
            "LAT_DECIMAL": "39.1754",
            "LONG_DECIMAL": "-76.6684",
        }
    )
    fix = FixRecord(
        {"FIX_NAME": "PALEO", "LAT_DECIMAL": "40.0", "LONG_DECIMAL": "-76.0"}
    )
    navaid = NavaidRecord(
        {"NAME": "Baltimore", "LAT_DECIMAL": "39.2", "LONG_DECIMAL": "-76.7"}
    )

    assert str(airport) == (
        "Airport: Baltimore/Washington International (39.1754, -76.6684)"
    )
    assert str(fix) == "Fix: PALEO (40.0, -76.0)"
    assert str(navaid) == "Navaid: Baltimore (39.2, -76.7)"


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


def test_airport_repository_accepts_single_token_helipad_runway_id():
    """A helipad ``RWY_ID`` like ``"H1"`` has one end, not a reciprocal pair."""
    tables = {
        "APT_BASE": pd.DataFrame([{"ARPT_ID": "AL39", "ICAO_ID": ""}]),
        "APT_RWY": pd.DataFrame([{"ARPT_ID": "AL39", "RWY_ID": "H1"}]),
        "APT_RWY_END": pd.DataFrame([{"ARPT_ID": "AL39", "RWY_END_ID": "H1"}]),
    }

    airport = AirportRepository(tables).get("AL39")

    assert airport.runways[0]["RWY_ID"] == "H1"
    assert airport.runway_ends[0]["RWY_END_ID"] == "H1"


def test_airport_repository_rejects_single_token_runway_missing_its_end():
    tables = {
        "APT_BASE": pd.DataFrame([{"ARPT_ID": "AL39", "ICAO_ID": ""}]),
        "APT_RWY": pd.DataFrame([{"ARPT_ID": "AL39", "RWY_ID": "H1"}]),
        "APT_RWY_END": pd.DataFrame(columns=["ARPT_ID", "RWY_END_ID"]),
    }

    with pytest.raises(SchemaMismatchError, match="reciprocal runway-end"):
        AirportRepository(tables).get("AL39")


def test_airport_repository_reuses_its_related_table_index_across_lookups():
    """Repeated lookups must not rescan APT_RWY's ARPT_ID column each time."""
    tables = {
        "APT_BASE": pd.DataFrame(
            [
                {"ARPT_ID": "BWI", "ICAO_ID": "KBWI"},
                {"ARPT_ID": "DCA", "ICAO_ID": "KDCA"},
            ]
        ),
        "APT_RWY": pd.DataFrame(
            [
                {"ARPT_ID": "BWI", "RWY_ID": "10/28"},
                {"ARPT_ID": "DCA", "RWY_ID": "01/19"},
            ]
        ),
        "APT_RWY_END": pd.DataFrame(
            [
                {"ARPT_ID": "BWI", "RWY_END_ID": "10"},
                {"ARPT_ID": "BWI", "RWY_END_ID": "28"},
                {"ARPT_ID": "DCA", "RWY_END_ID": "01"},
                {"ARPT_ID": "DCA", "RWY_END_ID": "19"},
            ]
        ),
    }
    repository = AirportRepository(tables)

    repository.get("BWI")
    index_after_first_lookup = dict(repository._related_indexes)
    repository.get("DCA")

    assert repository._related_indexes.keys() == index_after_first_lookup.keys()
    for key, frame in index_after_first_lookup.items():
        assert repository._related_indexes[key] is frame


def test_airport_record_associates_optional_ils_component_collections(fixture_nasr):
    nasr, _ = fixture_nasr

    airport = nasr.airports.get("BWI")

    assert airport.ils[0]["ARPT_ID"] == "BWI"
    assert airport.dmes[0]["ARPT_ID"] == "BWI"
    assert airport.glide_slopes[0]["ARPT_ID"] == "BWI"
    assert airport.markers[0]["ARPT_ID"] == "BWI"

    reduced = AirportRepository({"APT_BASE": nasr["APT_BASE"]})
    assert reduced.get("BWI").ils == ()


def test_marker_record_exposes_its_own_columns_not_military_operation_columns():
    """ILS_MKR has MARKER_ID_BEACON/COMPASS_LOCATOR_NAME, not MIL_OPS_CALL/HRS."""
    marker = MarkerRecord(
        {
            "MARKER_ID_BEACON": "AN",
            "COMPASS_LOCATOR_NAME": "BOGGA",
        }
    )

    assert marker.marker_id_beacon == "AN"
    assert marker.compass_locator_name == "BOGGA"
    assert MarkerRecord({"MARKER_ID_BEACON": ""}).marker_id_beacon is None


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


def test_record_repository_reuses_its_identifier_column_index_across_lookups():
    """Repeated identifier lookups on the same column must not rescan it."""
    repository = RecordRepository(
        pd.DataFrame(
            [
                {"NAV_ID": "ABC"},
                {"NAV_ID": "DEF"},
            ]
        ),
        entity_type="Navaid",
        identifier_columns=("NAV_ID",),
    )

    repository.get("ABC")
    index_after_first_lookup = dict(repository._normalized_indexes)
    repository.get("DEF")

    assert repository._normalized_indexes.keys() == index_after_first_lookup.keys()
    for column, index in index_after_first_lookup.items():
        assert repository._normalized_indexes[column] is index


def test_record_repository_uses_positions_for_high_cardinality_identifier_index():
    """Fully unique identifiers must not materialize one DataFrame per group."""
    frame = pd.DataFrame({"FIX_ID": [f"FIX{number:05d}" for number in range(1_000)]})
    repository = RecordRepository(
        frame,
        entity_type="Fix",
        identifier_columns=("FIX_ID",),
    )

    assert repository.get(" fix00750 ")["FIX_ID"] == "FIX00750"
    index = repository._normalized_indexes["FIX_ID"]
    assert isinstance(index["FIX00750"], ndarray)
    assert index["FIX00750"].tolist() == [750]

    for builder in (
        RecordRepository._normalized_index,
        AirportRepository._related_index,
    ):
        source = "".join(inspect.getsource(builder).split())
        assert ".groupby(normalized).indices" in source
        assert "dict(tuple(" not in source


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


def test_navaid_record_exposes_typed_core_fields(fixture_nasr):
    nasr, _ = fixture_nasr
    navaid = nasr.navaid("UNIQ")

    assert navaid.nav_type == "VOR"
    assert navaid.high_artcc == "ZDC"
    assert navaid.low_artcc == "ZDC"
    assert navaid.latitude == 39.1
    assert navaid.longitude == -76.1
