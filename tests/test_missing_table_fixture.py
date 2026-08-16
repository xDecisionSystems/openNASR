"""The missing-table cycle removes only the optional ILS marker table."""

from pathlib import Path

from tools.build_synthetic_fixtures import MISSING_TABLE_CYCLE_STEM


def test_missing_table_cycle_omits_only_ils_marker_table():
    csv_root = (
        Path(__file__).parent
        / "fixtures"
        / "missing_table_cycle"
        / "CSV_Data"
        / MISSING_TABLE_CYCLE_STEM
    )

    names = {path.name for path in csv_root.glob("*.csv")}
    assert "ILS_MKR.csv" not in names
    assert {"APT_BASE.csv", "ILS_BASE.csv", "ILS_DME.csv", "ILS_GS.csv"} <= names
