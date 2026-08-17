"""Tests for optional package metadata."""

from importlib.metadata import metadata, requires


def test_duckdb_is_declared_only_as_an_optional_extra():
    """Keep the base installation free of DuckDB."""
    distribution_metadata = metadata("openNASR")
    assert "duckdb" in distribution_metadata.get_all("Provides-Extra", [])

    duckdb_requirements = [
        requirement
        for requirement in requires("openNASR") or []
        if requirement.lower().startswith("duckdb")
    ]
    assert duckdb_requirements == ['duckdb>=1.2.2; extra == "duckdb"']
