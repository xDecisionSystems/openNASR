from pathlib import Path


README = Path(__file__).parents[1] / "README.md"
USING_THE_LIBRARY = Path(__file__).parents[1] / "docs" / "using-the-library.md"


def test_readme_contains_current_api_examples():
    text = README.read_text(encoding="utf-8")

    for heading in ("## Quick start", "## Airports", "## Fixes", "## Navigation aids"):
        assert heading in text
    assert "nasr = NASR()" in text
    assert 'Airport("BWI", nasr)' in text
    assert 'FIX("AABEE", nasr)' in text
    assert 'NAVAID("ABR", nasr)' in text


def test_using_the_library_covers_setup_and_core_workflows():
    text = USING_THE_LIBRARY.read_text(encoding="utf-8")

    for name in ("NASR", "CycleManager", "RouteResolver", "PlottingIndex"):
        assert name in text
    for heading in (
        "## Download NASR data",
        "## Command-line interface",
        "## Where data is saved",
        "## Choose CSV or DuckDB",
        "## Coordinates and boundaries",
        "## Errors",
    ):
        assert heading in text
