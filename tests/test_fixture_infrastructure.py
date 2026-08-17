from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from openNASR.cycles import CycleManager
from openNASR.nasr import NASR


def test_extracted_cycle_fixture_has_legacy_layout(extracted_cycle: Path):
    assert (extracted_cycle / "CSV_Data").is_dir()


def test_fixture_cycle_archive_is_a_real_zip(fixture_cycle_archive: Path):
    with ZipFile(fixture_cycle_archive) as archive:
        assert (
            "CSV_Data/28DaySubscription_Effective_2099-01-01/APT_BASE.csv"
            in archive.namelist()
        )


def test_fixture_nasr_loads_task_2_1_cycle(fixture_nasr):
    nasr, cache_root = fixture_nasr

    assert cache_root.is_dir()
    assert set(nasr["APT_BASE"]["ARPT_ID"]) == {"BWI", "DCA"}


def test_core_fixture_loads_without_package_data(make_nasr_from_fixture):
    nasr, cache_root = make_nasr_from_fixture("core/pre_2026_09")

    assert cache_root.is_dir()
    assert set(nasr) == {
        "APT_BASE",
        "APT_RWY",
        "APT_RWY_END",
        "ILS_BASE",
        "ILS_DME",
        "ILS_GS",
        "ILS_MKR",
        "FIX_BASE",
        "NAV_BASE",
        "ARB_BASE",
        "ARB_SEG",
        "MAA_BASE",
        "MAA_CON",
        "MAA_RMK",
        "MAA_SHP",
    }
    assert set(nasr["APT_BASE"]["ARPT_ID"]) == {"BWI", "DCA"}
    assert len(nasr["NAV_BASE"].query("NAV_ID == 'DUP'")) == 2


def test_schema_only_fixture_loads_every_csv(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("schema_only/nasr_2026_09")

    assert len(nasr) == 87
    assert nasr["APT_RWY"].empty
    assert nasr["APT_RWY"].columns.tolist()[13:15] == [
        "PAVEMENT_CLASSIFICATION",
        "PCN_PCR_NUMBER",
    ]


def test_nasr_extracts_a_nested_csv_zip_matching_the_real_faa_archive_layout(
    tmp_path,
):
    """Real FAA archives nest a second ZIP (``CSV_Data/<inner>.zip``)
    containing the CSVs directly, rather than an already-extracted
    directory. NASR must extract that inner archive itself."""

    outer_archive = tmp_path / "28DaySubscription_Effective_2099-01-04.zip"
    with ZipFile(outer_archive, "w", compression=ZIP_DEFLATED) as outer:
        inner_bytes_path = tmp_path / "inner.zip"
        with ZipFile(inner_bytes_path, "w", compression=ZIP_DEFLATED) as inner:
            inner.writestr("APT_BASE.csv", "ARPT_ID\nBWI\n")
        outer.write(
            inner_bytes_path, "CSV_Data/28DaySubscription_Effective_2099-01-04.zip"
        )

    cache_root = tmp_path / "cache"
    manager = CycleManager(cache_root)
    manager.import_archive(outer_archive)

    nasr = NASR(cache_dir=cache_root)

    assert set(nasr["APT_BASE"]["ARPT_ID"]) == {"BWI"}
