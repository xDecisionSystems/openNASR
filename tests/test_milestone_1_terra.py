"""Regression coverage for the Terra-owned Milestone 1 fixes."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pandas import DataFrame

from openNASR.airport import Airport
from openNASR.basictypes import Raw
from openNASR.exceptions import (
    AmbiguousRecordError,
    CycleNotFoundError,
    RecordNotFoundError,
    SchemaMismatchError,
)
from openNASR.fix import FIX
from openNASR.nav import NAVAID
from openNASR.nasr import NASR


def test_airport_faa_and_icao_lookups_have_identical_related_collections(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    airport_by_faa = Airport("BWI", nasr)
    airport_by_icao = Airport("KBWI", nasr)

    assert airport_by_faa.faa_id == airport_by_icao.faa_id == "BWI"
    for collection_name in ("rwy", "rwyend", "ils", "dme", "gs", "mkr"):
        faa_collection = getattr(airport_by_faa, collection_name)
        icao_collection = getattr(airport_by_icao, collection_name)
        assert faa_collection.ids
        assert faa_collection.ids == icao_collection.ids

    assert airport_by_faa.rwy.getRawByID("10/28").RWY_LEN == 5000
    assert airport_by_faa.rwy.getRaw()["10/28"].RWY_ID == "10/28"


@pytest.mark.parametrize("identifier", ["BWI", "KBWI"])
def test_airport_identifiers_canonicalize_to_the_faa_identifier(
    make_nasr_from_fixture, identifier
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    exists, matched_column, faa_identifier = nasr.isAirport(identifier)

    assert exists
    assert matched_column == "ARPT_ID"
    assert faa_identifier == "BWI"
    assert len(nasr._NASR__legacy_indexes) == (1 if identifier == "BWI" else 2)


@pytest.mark.parametrize("identifier", [" bwi ", "bwi", "kbwi", "Bwi"])
def test_isairport_resolves_identifiers_case_insensitively(
    make_nasr_from_fixture, identifier
):
    """The legacy resolver must agree with the modern AirportRepository,
    which already normalizes identifiers via strip+upper."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    exists, matched_column, faa_identifier = nasr.isAirport(identifier)

    assert exists
    assert matched_column == "ARPT_ID"
    assert faa_identifier == "BWI"


@pytest.mark.parametrize("identifier", ["bwi", "kbwi"])
def test_legacy_airport_constructor_resolves_identifiers_case_insensitively(
    make_nasr_from_fixture, identifier
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    airport = Airport(identifier, nasr)

    assert airport.faa_id == "BWI"


def test_legacy_airport_reuses_related_row_mappings_but_not_raw_objects(
    make_nasr_from_fixture, monkeypatch
):
    """Warm legacy airport assembly must not rescan or reconvert child rows."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")
    first = Airport("BWI", nasr)
    first_runway_raw = first.rwy.getRawByID("10/28")

    def fail_to_dict(*_args, **_kwargs):
        raise AssertionError("warm Airport construction converted a DataFrame row")

    monkeypatch.setattr(DataFrame, "to_dict", fail_to_dict)
    second = Airport("BWI", nasr)

    assert second.rwy.ids == first.rwy.ids == ["10/28"]
    assert second.rwy.getRawByID("10/28").RWY_LEN == 5000
    assert second.rwy.getRawByID("10/28") is not first_runway_raw


def test_legacy_fix_constructor_resolves_identifier_case_insensitively(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    assert nasr.isFix(" aabee ")
    cache = nasr._NASR__legacy_indexes
    key = (id(nasr["FIX_BASE"]), "FIX_ID")
    cached_index = cache[key]
    fix = FIX("aabee", nasr)

    assert fix.FIX_ID == "AABEE"
    assert isinstance(fix.getRaw(), SimpleNamespace)
    assert nasr._NASR__legacy_indexes[key] is cached_index


def test_legacy_navaid_constructor_resolves_identifier_case_insensitively(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    navaid = NAVAID("uniq", nasr)

    assert navaid.NAV_ID == "UNIQ"
    assert isinstance(navaid.getRaw(), SimpleNamespace)
    assert len(nasr._NASR__legacy_indexes) == 1


def test_raw_attribute_delegation_is_safe():
    raw = Raw(SimpleNamespace(SITE_ELEVATION=123))

    assert raw.SITE_ELEVATION == 123
    with pytest.raises(AttributeError, match="Raw.*missing"):
        _ = raw.missing


def test_navaid_lookup_filters_and_typed_errors(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    assert NAVAID("UNIQ", nasr).NAV_ID == "UNIQ"
    assert NAVAID("DUP", nasr, inState="IN", nav_type="VOR").STATE_CODE == "IN"

    with pytest.raises(AmbiguousRecordError) as ambiguous:
        NAVAID("DUP", nasr)
    assert len(ambiguous.value.candidates) == 2

    with pytest.raises(RecordNotFoundError) as missing:
        NAVAID("DUP", nasr, inState="FL")
    assert missing.value.filters == {"in_state": "FL"}

    with pytest.raises(RecordNotFoundError):
        NAVAID("MISSING", nasr)


def test_airport_and_fix_construction_against_core_fixture(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    assert Airport("BWI", nasr).rwy["10/28"].length == 5000
    assert FIX("AABEE", nasr).FIX_ID == "AABEE"
    with pytest.raises(RecordNotFoundError):
        Airport("MISSING", nasr)
    with pytest.raises(RecordNotFoundError):
        FIX("MISSING", nasr)


def test_nasr_cycle_selection_artcc_and_preload_behavior(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")
    assert nasr.artccs.get("ZOB").high.getShape.is_valid
    with pytest.raises(NotImplementedError, match="preloadAll"):
        NASR(preloadAll=True)


@pytest.mark.skipif(
    not os.environ.get("OPENNASR_REAL_CYCLE_DIR"),
    reason="requires an explicitly configured real FAA NASR cycle cache directory",
)
def test_real_cycle_selection_uses_configured_cycle():
    cache_root = Path(os.environ["OPENNASR_REAL_CYCLE_DIR"])

    exact_cycle = NASR(useDate="2026-08-06", cache_dir=cache_root)

    assert exact_cycle._NASR__useDate == "2026-08-06"


def test_missing_cycle_raises_typed_error(tmp_path):
    with pytest.raises(CycleNotFoundError) as error:
        NASR(useDate="2026-08-06", cache_dir=tmp_path)

    assert "2026-08-06" in str(error.value)
    assert "28DaySubscription_Effective_YYYY-MM-DD.zip" in str(error.value)


def test_exact_cycle_request_never_silently_falls_back_to_an_earlier_cycle(
    fixture_cycle_archive, tmp_path
):
    """An explicitly requested cycle date must be exact, per PLAN.md's
    "Behavioral requirements": a cached earlier cycle existing must never
    cause a silent substitution."""
    from openNASR.cycles import CycleManager

    cache_root = tmp_path / "cache"
    manager = CycleManager(cache_root)
    manager.import_archive(fixture_cycle_archive)

    with pytest.raises(CycleNotFoundError) as error:
        NASR(cycle="2200-01-01", cache_dir=cache_root)

    assert "2200-01-01" in str(error.value)


def test_nasr_reads_from_the_supplied_cache_dir_and_never_touches_package_data(
    fixture_cycle_archive, tmp_path
):
    from openNASR.cycles import CycleManager

    cache_root = tmp_path / "cache"
    manager = CycleManager(cache_root)
    manager.import_archive(fixture_cycle_archive)
    package_data_dir = Path(__file__).parents[1] / "openNASR" / "data"
    before = set(package_data_dir.rglob("*")) if package_data_dir.exists() else set()

    nasr = NASR(cache_dir=cache_root)
    nasr["APT_BASE"]

    after = set(package_data_dir.rglob("*")) if package_data_dir.exists() else set()
    assert after == before
    assert str(cache_root) in str(nasr._NASR__useDateCSVFolder)


def test_schema_drift_on_one_table_does_not_block_an_unrelated_valid_table(
    make_nasr_from_fixture,
):
    """A SchemaMismatchError for one table must not prevent constructing NASR
    or using a different, unrelated table that passes validation."""
    nasr, _ = make_nasr_from_fixture("malformed")

    # APT_BASE is missing ARPT_ID in this fixture and raises on access...
    with pytest.raises(SchemaMismatchError):
        nasr["APT_BASE"]

    # ...but an unrelated table that is not drifted still loads normally.
    assert not nasr["NAV_BASE"].empty


def test_nasr_does_not_load_tables_until_they_are_requested(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    assert nasr.is_loaded("APT_BASE") is False

    nasr["APT_BASE"]

    assert nasr.is_loaded("APT_BASE") is True
    assert nasr.is_loaded("NAV_BASE") is False


def test_requesting_one_aggregate_does_not_load_unrelated_aggregates_tables(
    make_nasr_from_fixture,
):
    """Looking up one entity (an airport) must load only that entity's own
    tables (APT_*/ILS_*), never a different, unrelated family's tables
    (FIX_BASE, NAV_BASE, ARB_BASE/ARB_SEG) that simply happen to be present
    in the same cycle."""
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")
    unrelated_tables = ("FIX_BASE", "NAV_BASE", "ARB_BASE", "ARB_SEG")
    for table in unrelated_tables:
        assert nasr.is_loaded(table) is False

    nasr.airport("BWI")

    assert nasr.is_loaded("APT_BASE") is True
    for table in unrelated_tables:
        assert nasr.is_loaded(table) is False


def test_nasr_table_method_returns_cached_frame_or_a_defensive_copy(
    make_nasr_from_fixture,
):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    shared = nasr.table("APT_BASE")
    assert nasr.table("APT_BASE") is shared

    isolated = nasr.table("APT_BASE", copy=True)
    isolated.loc[0, "ARPT_ID"] = "MUTATED"
    assert nasr.table("APT_BASE").loc[0, "ARPT_ID"] != "MUTATED"
