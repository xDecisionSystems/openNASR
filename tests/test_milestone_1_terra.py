"""Regression coverage for the Terra-owned Milestone 1 fixes."""

from types import SimpleNamespace

import pytest

from openNASR.airport import Airport
from openNASR.basictypes import Raw
from openNASR.exceptions import (
    AmbiguousRecordError,
    CycleNotFoundError,
    RecordNotFoundError,
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
    exact_cycle = NASR(useDate="2026-08-06")

    assert exact_cycle._NASR__useDate == "2026-08-06"
    nasr.loadARTCC()
    assert nasr.artcc.getARTCC("ZOB").high.getShape.is_valid
    with pytest.raises(NotImplementedError, match="preloadAll"):
        NASR(preloadAll=True)


def test_missing_cycle_raises_typed_error(monkeypatch, tmp_path):
    import openNASR.nasr as nasr_module

    monkeypatch.setattr(nasr_module, "__file__", str(tmp_path / "nasr.py"))

    with pytest.raises(CycleNotFoundError) as error:
        NASR(useDate="2026-08-06")

    assert "2026-08-06" in str(error.value)
    assert "28DaySubscription_Effective_YYYY-MM-DD.zip" in str(error.value)
