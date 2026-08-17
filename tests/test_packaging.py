"""Tests for optional package metadata."""

from importlib.metadata import metadata, requires
from pathlib import Path
import tomllib


PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


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


def test_public_release_metadata_uses_modern_license_and_project_urls():
    configuration = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = configuration["project"]

    assert configuration["build-system"]["requires"] == ["setuptools>=77.0.3"]
    assert project["license"] == "GPL-3.0-only"
    assert project["license-files"] == ["LICENSE"]
    assert project["readme"] == "README.md"
    assert configuration["tool"]["setuptools"]["package-data"]["openNASR"] == [
        "py.typed"
    ]
    assert {"Homepage", "Documentation", "Repository", "Issues", "Changelog"} <= (
        project["urls"].keys()
    )
