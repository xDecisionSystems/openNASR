"""Tests for optional package metadata."""

from importlib.metadata import metadata, requires
from pathlib import Path
import tomllib


PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


def test_duckdb_is_a_required_dependency_capped_below_two():
    """The 2.0.0 wheel needs AVX2; stay on 1.x until installers probe for it."""
    duckdb_requirements = [
        requirement
        for requirement in requires("openNASR") or []
        if requirement.lower().startswith("duckdb")
    ]
    assert duckdb_requirements == ["duckdb<2,>=1.2.2"]
    assert "duckdb" not in metadata("openNASR").get_all("Provides-Extra", [])


def test_public_release_metadata_uses_modern_license_and_project_urls():
    configuration = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = configuration["project"]

    assert configuration["build-system"]["requires"] == ["setuptools>=77.0.3"]
    assert project["license"] == "GPL-3.0-only"
    assert project["license-files"] == ["LICENSE"]
    assert project["readme"] == "README.md"
    assert configuration["tool"]["setuptools"]["package-data"]["openNASR"] == [
        "py.typed",
        "schema_manifests/*.json",
    ]
    assert {"Homepage", "Documentation", "Repository", "Issues", "Changelog"} <= (
        project["urls"].keys()
    )


def test_schema_manifests_ship_inside_the_package():
    """An installed wheel has no ``tests/`` tree; the catalog must not need one."""

    from pathlib import Path

    import openNASR
    from openNASR.schemas import SchemaCatalog

    package = Path(openNASR.__file__).parent
    assert (package / "schema_manifests" / "nasr_2026_09.json").is_file()
    assert Path(SchemaCatalog().manifest_dir) == package / "schema_manifests"
    assert set(SchemaCatalog.SUPPORTED_SCHEMA_IDS) <= {
        path.stem for path in (package / "schema_manifests").glob("*.json")
    }
