"""Fixture-cycle helpers that never use package data, user caches, or a network."""

from __future__ import annotations

from pathlib import Path
from shutil import copytree
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from openNASR.nasr import NASR


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
FIXTURE_DATES = {
    "core/pre_2026_09": "2026-08-06",
    "schema_only/pre_2026_09": "2026-08-06",
    "schema_only/nasr_2026_09": "2026-09-03",
    "duckdb_parity/pre_2026_09": "2026-08-06",
    "duckdb_parity/nasr_2026_09": "2026-09-03",
    "malformed": "2099-01-02",
    "missing_table_cycle": "2099-01-03",
}
CORE_CYCLE_DATE = "2099-01-01"
CORE_CYCLE_STEM = f"28DaySubscription_Effective_{CORE_CYCLE_DATE}"


def _create_fixture_archive(source: Path, archive: Path) -> None:
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
        for path in sorted(source.rglob("*.csv")):
            output.write(path, path.relative_to(source))


@pytest.fixture(scope="session")
def cycle_cache_template(tmp_path_factory):
    """Build each fixture cycle's cache (archive, CSVs, DuckDB) once per session.

    Building a DuckDB artifact is the slow part of constructing ``NASR``;
    tests copy the finished cache (preserving mtimes, so the artifact stays
    current) instead of rebuilding it for every test.
    """

    templates: dict[str, Path] = {}

    def get(key: str, source: Path, archive_name: str) -> Path:
        if key not in templates:
            root = tmp_path_factory.mktemp("template") / "cache"
            (root / "archives").mkdir(parents=True)
            _create_fixture_archive(source, root / "archives" / archive_name)
            NASR(cache_dir=root)
            templates[key] = root
        return templates[key]

    return get


@pytest.fixture
def extracted_cycle() -> Path:
    """Return the checked-in Task 2.1 extracted fixture cycle."""

    return FIXTURE_ROOT / "cycle"


@pytest.fixture
def fixture_cycle_archive(extracted_cycle: Path, tmp_path: Path) -> Path:
    """Build a real NASR archive from the Task 2.1 extracted cycle."""

    archive = tmp_path / f"{CORE_CYCLE_STEM}.zip"
    _create_fixture_archive(extracted_cycle, archive)
    return archive


@pytest.fixture
def fixture_nasr(cycle_cache_template, extracted_cycle, tmp_path):
    """Construct ``NASR`` from the Task 2.1 archive in a temporary cache."""

    template = cycle_cache_template(
        "core-cycle", extracted_cycle, f"{CORE_CYCLE_STEM}.zip"
    )
    cache_root = tmp_path / "cycle_cache"
    copytree(template, cache_root)
    return NASR(cache_dir=cache_root), cache_root


@pytest.fixture
def make_nasr_from_fixture(cycle_cache_template, tmp_path):
    """Construct ``NASR`` against a synthetic fixture in a temporary cache."""

    def make(fixture_name: str) -> tuple[NASR, Path]:
        try:
            cycle_date = FIXTURE_DATES[fixture_name]
        except KeyError as error:
            raise ValueError(f"Unknown NASR fixture: {fixture_name}") from error

        template = cycle_cache_template(
            fixture_name,
            FIXTURE_ROOT / fixture_name,
            f"28DaySubscription_Effective_{cycle_date}.zip",
        )
        cache_root = tmp_path / fixture_name.replace("/", "_")
        copytree(template, cache_root)
        return NASR(cache_dir=cache_root), cache_root

    return make
