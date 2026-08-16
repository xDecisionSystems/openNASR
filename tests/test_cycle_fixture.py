"""The extracted fixture cycle matches the legacy NASR loader layout."""

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
