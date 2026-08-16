"""Cycle-cache configuration tests."""

from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

from openNASR import cycles
from openNASR.exceptions import ArchiveError
from openNASR.cycles import (
    CycleManager,
    locate_csv_source,
    parse_archive_date,
    read_cycle_date,
    resolve_cache_dir,
    sha256_file,
    validate_archive,
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


def test_import_archive_copies_the_source_without_modifying_it(tmp_path):
    source = tmp_path / "28DaySubscription_Effective_2026-08-06.zip"
    with ZipFile(source, "w") as archive:
        archive.writestr("fixture.txt", "fixture archive")
    source_bytes = source.read_bytes()

    cycle = CycleManager(tmp_path / "cache").import_archive(source)

    assert source.read_bytes() == source_bytes
    assert cycle.effective_date == date(2026, 8, 6)
    assert cycle.archive_path.read_bytes() == source_bytes


def test_downloads_use_a_temporary_part_path(tmp_path):
    part_path = CycleManager(tmp_path).download_part_path(date(2026, 8, 6))

    assert part_path.parent == tmp_path / "downloads"
    assert part_path.name.endswith(".zip.part")
    assert not part_path.exists()


def test_download_data_is_written_in_chunks_to_the_part_file(tmp_path):
    manager = CycleManager(tmp_path)

    part_path = manager.write_download_part(date(2026, 8, 6), [b"first", b"second"])

    assert part_path.read_bytes() == b"firstsecond"


def test_interrupted_download_removes_partial_file(tmp_path):
    manager = CycleManager(tmp_path)

    def interrupted_chunks():
        yield b"partial"
        raise OSError("connection interrupted")

    with pytest.raises(OSError, match="interrupted"):
        manager.write_download_part(date(2026, 8, 6), interrupted_chunks())

    assert not manager.download_part_path(date(2026, 8, 6)).exists()


def test_completed_download_is_atomically_published_to_archives(tmp_path):
    manager = CycleManager(tmp_path)
    manager.write_download_part(date(2026, 8, 6), [b"archive"])

    cycle = manager.publish_download(date(2026, 8, 6))

    assert cycle.archive_path.read_bytes() == b"archive"
    assert not manager.download_part_path(date(2026, 8, 6)).exists()


def test_sha256_digest_and_metadata_are_stored_for_an_archive(tmp_path):
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"archive contents")
    manager = CycleManager(tmp_path / "cache")

    metadata = manager.store_sha256_metadata(archive)

    assert sha256_file(archive) in metadata.read_text(encoding="utf-8")


def test_html_and_non_zip_archives_are_rejected(tmp_path):
    html = tmp_path / "error.html"
    html.write_text("<html>error</html>", encoding="utf-8")
    invalid = tmp_path / "invalid.zip"
    invalid.write_bytes(b"not a zip")

    for archive in (html, invalid):
        with pytest.raises(ValueError, match="Invalid NASR archive"):
            validate_archive(archive)


def test_archive_is_extracted_and_published_atomically(tmp_path):
    archive = tmp_path / "28DaySubscription_Effective_2026-08-06.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("nested/CSV_Data/APT_BASE.csv", "ARPT_ID\nBWI\n")

    cycle = CycleManager(tmp_path / "cache").extract_archive(archive)

    assert cycle.data_path.name == "2026-08-06"
    assert (cycle.data_path / "nested/CSV_Data/APT_BASE.csv").is_file()
    assert not list(cycle.data_path.parent.glob(".extract-*"))

    repeated = CycleManager(tmp_path / "cache").extract_archive(archive)
    assert repeated.data_path == cycle.data_path
    assert not list(cycle.data_path.parent.glob(".extract-*"))


@pytest.mark.parametrize("member", ["../escape.csv", "/absolute.csv"])
def test_archive_extraction_rejects_unsafe_members(tmp_path, member):
    archive = tmp_path / "28DaySubscription_Effective_2026-08-06.zip"
    with ZipFile(archive, "w") as output:
        output.writestr(member, "unsafe")

    with pytest.raises(ArchiveError, match="Unsafe archive member"):
        CycleManager(tmp_path / "cache").extract_archive(archive)

    assert not (tmp_path / "escape.csv").exists()


def test_csv_source_locator_accepts_nested_directories_and_archives(tmp_path):
    directory_cycle = tmp_path / "directory-cycle"
    csv_dir = directory_cycle / "arbitrary" / "CSV_Data" / "cycle"
    csv_dir.mkdir(parents=True)
    (csv_dir / "APT_BASE.csv").write_text("ARPT_ID\nBWI\n", encoding="utf-8")
    archive_cycle = tmp_path / "archive-cycle"
    archive_cycle.mkdir()
    nested_archive = archive_cycle / "arbitrary" / "faa-data.zip"
    nested_archive.parent.mkdir()
    with ZipFile(nested_archive, "w") as output:
        output.writestr("APT_BASE.csv", "ARPT_ID\nBWI\n")

    assert locate_csv_source(directory_cycle) == csv_dir
    assert locate_csv_source(archive_cycle) == nested_archive


def test_get_reuses_cached_cycle_without_rewriting_archive(tmp_path):
    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir(parents=True)
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("APT_BASE.csv", "ARPT_ID\nBWI\n")
    before = archive.stat().st_mtime_ns

    cycle = manager.get(date(2026, 8, 6))

    assert cycle.archive_path == archive
    assert archive.stat().st_mtime_ns == before
    assert manager.get(date(2026, 8, 6), force=True) is None
