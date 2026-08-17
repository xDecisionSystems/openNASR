"""Semantic contracts for the tiny CSV/DuckDB parity cycles."""

from __future__ import annotations

from pathlib import Path
import csv


def _raw_rows(generation: str, table: str) -> list[dict[str, str]]:
    path = (
        Path(__file__).parent
        / "fixtures"
        / "duckdb_parity"
        / generation
        / "CSV_Data"
        / generation
        / f"{table}.csv"
    )
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_parity_fixture_preserves_text_edge_cases(make_nasr_from_fixture):
    for generation in ("pre_2026_09", "nasr_2026_09"):
        nasr, _ = make_nasr_from_fixture(f"duckdb_parity/{generation}")
        fixes = nasr["FIX_BASE"]

        assert len(fixes) == 2
        assert fixes["FIX_ID"].tolist() == ["DUP", "DUP"]
        rows = _raw_rows(generation, "FIX_BASE")
        assert rows[0]["MIN_RECEP_ALT"] == "000010"
        assert fixes.loc[0, "CHARTING_REMARK"] == "Comma, and newline\nremark"
        assert fixes.loc[1, "CHARTING_REMARK"] == "Café waypoint"
        assert rows[1]["FIX_USE_CODE"] == ""


def test_parity_fixture_retains_generation_specific_runway_schema(
    make_nasr_from_fixture,
):
    old, _ = make_nasr_from_fixture("duckdb_parity/pre_2026_09")
    current, _ = make_nasr_from_fixture("duckdb_parity/nasr_2026_09")

    assert "PCN" in old["APT_RWY"]
    assert "PAVEMENT_CLASSIFICATION" not in old["APT_RWY"]
    assert _raw_rows("pre_2026_09", "APT_RWY")[0]["PCN"] == "00058"

    assert "PCN" not in current["APT_RWY"]
    assert current["APT_RWY"].columns.tolist()[13:15] == [
        "PAVEMENT_CLASSIFICATION",
        "PCN_PCR_NUMBER",
    ]
    assert _raw_rows("nasr_2026_09", "APT_RWY")[0]["PCN_PCR_NUMBER"] == "58/F/B/W/T"


def test_parity_fixture_files_are_tiny_text_only():
    root = Path(__file__).parent / "fixtures" / "duckdb_parity"
    files = sorted(root.rglob("*.csv"))
    assert {path.name for path in files} == {"APT_RWY.csv", "FIX_BASE.csv"}
    assert all(path.stat().st_size < 4_000 for path in files)
    assert not list(root.rglob("*.zip"))
