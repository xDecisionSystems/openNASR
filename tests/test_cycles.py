"""Cycle-cache configuration tests."""

from datetime import date
from pathlib import Path

from openNASR import cycles
from openNASR.cycles import (
    CycleManager,
    parse_archive_date,
    read_cycle_date,
    resolve_cache_dir,
)


def test_explicit_cache_directory_has_highest_precedence(monkeypatch, tmp_path):
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("OPENNASR_CACHE_DIR", str(tmp_path / "environment"))
    monkeypatch.setattr(cycles, "user_cache_dir", lambda _: str(tmp_path / "default"))

    assert resolve_cache_dir(explicit) == explicit
    assert CycleManager(explicit).cache_dir == explicit


def test_environment_cache_directory_overrides_platform_default(monkeypatch, tmp_path):
    configured = tmp_path / "environment"
    monkeypatch.setenv("OPENNASR_CACHE_DIR", str(configured))
    monkeypatch.setattr(cycles, "user_cache_dir", lambda _: str(tmp_path / "default"))

    assert resolve_cache_dir() == configured


def test_platform_cache_directory_is_used_without_overrides(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENNASR_CACHE_DIR", raising=False)
    default = tmp_path / "platform-default"
    monkeypatch.setattr(cycles, "user_cache_dir", lambda _: str(default))

    assert resolve_cache_dir() == Path(default)


def test_archives_and_extracted_cycles_are_discovered_independently(tmp_path):
    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir()
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    archive.touch()
    manager.cycles_dir.mkdir()
    extracted = manager.cycles_dir / "2026-09-03"
    extracted.mkdir()

    assert manager.archive_paths() == (archive,)
    assert manager.extracted_paths() == (extracted,)


def test_archive_dates_are_validated_and_ordered_by_parsed_dates(tmp_path):
    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir()
    later = manager.archives_dir / "28DaySubscription_Effective_2026-09-03.zip"
    earlier = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    invalid = manager.archives_dir / "28DaySubscription_Effective_2026-99-99.zip"
    for archive in (later, earlier, invalid):
        archive.touch()

    assert parse_archive_date(earlier) == date(2026, 8, 6)
    assert parse_archive_date(invalid) is None
    assert manager.archive_paths() == (earlier, later)


def test_cycle_date_prefers_validated_extracted_metadata(tmp_path):
    cycle_path = tmp_path / "cycles" / "2026-09-03"
    cycle_path.mkdir(parents=True)
    (cycle_path / "metadata.json").write_text(
        '{"effective_date": "2026-09-03"}', encoding="utf-8"
    )
    archive = tmp_path / "28DaySubscription_Effective_2026-08-06.zip"

    assert read_cycle_date(data_path=cycle_path, archive_path=archive) == date(
        2026, 9, 3
    )


def test_cycle_date_falls_back_to_a_validated_archive_name(tmp_path):
    archive = tmp_path / "28DaySubscription_Effective_2026-08-06.zip"

    assert read_cycle_date(archive_path=archive) == date(2026, 8, 6)
