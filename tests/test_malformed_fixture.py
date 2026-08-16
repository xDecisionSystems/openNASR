"""Malformed fixture inputs are intentionally small and deterministic."""

from pathlib import Path

from tools.build_synthetic_fixtures import MALFORMED_CYCLE_STEM


def test_malformed_cycle_omits_required_airport_identifier_column():
    path = (
        Path(__file__).parent
        / "fixtures"
        / "malformed"
        / "CSV_Data"
        / MALFORMED_CYCLE_STEM
        / "APT_BASE.csv"
    )

    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert "ARPT_ID" not in header
