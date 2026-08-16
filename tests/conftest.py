"""Fixture-cycle helpers that never use package data, user caches, or a network."""

from __future__ import annotations

from pathlib import Path
from shutil import copyfile
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from openNASR.nasr import NASR
import openNASR.nasr as nasr_module


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
FIXTURE_DATES = {
    "core/pre_2026_09": "2026-08-06",
    "schema_only/pre_2026_09": "2026-08-06",
    "schema_only/nasr_2026_09": "2026-09-03",
    "malformed": "2099-01-02",
    "missing_table_cycle": "2099-01-03",
}
CORE_CYCLE_DATE = "2099-01-01"
CORE_CYCLE_STEM = f"28DaySubscription_Effective_{CORE_CYCLE_DATE}"


def _create_fixture_archive(source: Path, archive: Path) -> None:
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
        for path in sorted(source.rglob("*.csv")):
            output.write(path, path.relative_to(source))


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
def fixture_nasr(
    fixture_cycle_archive: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[NASR, Path]:
    """Construct ``NASR`` from the Task 2.1 archive in a temporary cache."""

    cache_root = tmp_path / "cycle_cache"
    zip_dir = cache_root / "data" / "zip"
    zip_dir.mkdir(parents=True)
    copyfile(fixture_cycle_archive, zip_dir / fixture_cycle_archive.name)

    monkeypatch.setattr(nasr_module, "__file__", str(cache_root / "nasr.py"))
    return NASR(), cache_root


@pytest.fixture
def make_nasr_from_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Construct ``NASR`` against a synthetic fixture in a temporary cache."""

    def make(fixture_name: str) -> tuple[NASR, Path]:
        try:
            cycle_date = FIXTURE_DATES[fixture_name]
        except KeyError as error:
            raise ValueError(f"Unknown NASR fixture: {fixture_name}") from error

        source = FIXTURE_ROOT / fixture_name
        cache_root = tmp_path / fixture_name.replace("/", "_")
        zip_dir = cache_root / "data" / "zip"
        zip_dir.mkdir(parents=True)
        archive = zip_dir / f"28DaySubscription_Effective_{cycle_date}.zip"
        _create_fixture_archive(source, archive)

        monkeypatch.setattr(nasr_module, "__file__", str(cache_root / "nasr.py"))
        return NASR(), cache_root

    return make
