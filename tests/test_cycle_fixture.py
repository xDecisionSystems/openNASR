"""The extracted fixture cycle matches the legacy NASR loader layout."""

import csv
from pathlib import Path

from tools.build_synthetic_fixtures import CORE_CYCLE_STEM


def test_cycle_fixture_has_expected_nested_layout_and_core_tables():
    csv_root = (
        Path(__file__).parent
        / "fixtures"
        / "cycle"
        / "CSV_Data"
        / CORE_CYCLE_STEM
    )

    assert csv_root.is_dir()
    assert {
        "APT_BASE.csv",
        "APT_RWY.csv",
        "APT_RWY_END.csv",
        "ARB_BASE.csv",
        "ARB_SEG.csv",
        "FIX_BASE.csv",
        "ILS_BASE.csv",
        "ILS_DME.csv",
        "ILS_GS.csv",
        "ILS_MKR.csv",
        "NAV_BASE.csv",
    } <= {path.name for path in csv_root.glob("*.csv")}


def test_cycle_fixture_airport_base_is_minimal_and_has_two_identifiers():
    csv_root = (
        Path(__file__).parent
        / "fixtures"
        / "cycle"
        / "CSV_Data"
        / CORE_CYCLE_STEM
    )
    lines = (csv_root / "APT_BASE.csv").read_text(encoding="utf-8").splitlines()

    assert lines[0].split(",") == [
        "ARPT_ID",
        "ICAO_ID",
        "LAT_DECIMAL",
        "LONG_DECIMAL",
        "ELEV",
        "SITE_ELEVATION",
    ]
    assert len(lines) == 3
    assert {line.split(",")[0] for line in lines[1:]} == {"BWI", "DCA"}


def test_cycle_fixture_contains_reciprocal_runway_ends():
    csv_root = (
        Path(__file__).parent
        / "fixtures"
        / "cycle"
        / "CSV_Data"
        / CORE_CYCLE_STEM
    )
    runway_rows = (csv_root / "APT_RWY.csv").read_text(encoding="utf-8").splitlines()
    end_rows = (csv_root / "APT_RWY_END.csv").read_text(encoding="utf-8").splitlines()

    assert any("BWI" in row and "10/28" in row for row in runway_rows[1:])
    assert {row.split(",")[8] for row in end_rows[1:]} >= {"10", "28"}


def test_cycle_fixture_ils_components_share_runway_end_key():
    csv_root = (
        Path(__file__).parent
        / "fixtures"
        / "cycle"
        / "CSV_Data"
        / CORE_CYCLE_STEM
    )

    for table_name in ("ILS_BASE", "ILS_DME", "ILS_GS", "ILS_MKR"):
        with (csv_root / f"{table_name}.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        assert rows
        assert all(row["ARPT_ID"] == "BWI" for row in rows)
        assert all(row["RWY_END_ID"] == "10" for row in rows)


def test_cycle_fixture_contains_one_unique_fix():
    csv_root = (
        Path(__file__).parent
        / "fixtures"
        / "cycle"
        / "CSV_Data"
        / CORE_CYCLE_STEM
    )

    with (csv_root / "FIX_BASE.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["FIX_ID"] for row in rows] == ["AABEE"]
