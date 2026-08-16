from pathlib import Path


README = Path(__file__).parents[1] / "README.md"


def test_readme_contains_current_api_examples():
    text = README.read_text(encoding="utf-8")

    for heading in ("## Quick start", "## Airports", "## Fixes", "## Navigation aids"):
        assert heading in text
    assert "nasr = NASR()" in text
    assert 'Airport("BWI", nasr)' in text
    assert 'FIX("AABEE", nasr)' in text
    assert 'NAVAID("ABR", nasr)' in text
