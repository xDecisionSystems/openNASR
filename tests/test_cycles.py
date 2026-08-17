"""Cycle-cache configuration tests."""

from datetime import date
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from openNASR import cycles
from openNASR.exceptions import ArchiveError
from openNASR.exceptions import CycleNotFoundError
from openNASR.exceptions import DownloadError
from openNASR.cycles import (
    CycleManager,
    FaaCycleProvider,
    RemoteCycle,
    locate_csv_source,
    notify_if_update_available,
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


def test_available_cycles_unions_valid_archives_and_extracted_data(tmp_path):
    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir()
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    archive.touch()
    manager.cycles_dir.mkdir()
    (manager.cycles_dir / "2026-08-06").mkdir()
    (manager.cycles_dir / "2026-09-03").mkdir()
    (manager.cycles_dir / "not-a-cycle").mkdir()

    assert manager.available_cycles() == (date(2026, 8, 6), date(2026, 9, 3))


def test_latest_requires_a_cached_cycle_and_handles_independent_storage(tmp_path):
    manager = CycleManager(tmp_path)

    assert manager.available_cycles() == ()
    with pytest.raises(CycleNotFoundError, match=str(tmp_path)):
        manager.latest()

    manager.archives_dir.mkdir()
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("APT_BASE.csv", "ARPT_ID\nBWI\n")
    assert manager.latest().archive_path == archive

    archive.unlink()
    manager.cycles_dir.mkdir()
    extracted = manager.cycles_dir / "2026-09-03"
    extracted.mkdir()
    assert manager.latest().data_path == extracted


def test_remove_can_select_archive_or_extracted_data_independently(tmp_path):
    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir()
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    archive.touch()
    manager.cycles_dir.mkdir()
    extracted = manager.cycles_dir / "2026-08-06"
    extracted.mkdir()

    manager.remove(date(2026, 8, 6), archive=False)
    assert archive.exists()
    assert not extracted.exists()

    extracted.mkdir()
    manager.remove(date(2026, 8, 6), extracted=False)
    assert not archive.exists()
    assert extracted.exists()

    with pytest.raises(ValueError, match="At least one"):
        manager.remove(date(2026, 8, 6), archive=False, extracted=False)


def test_remove_reports_which_representations_actually_existed(tmp_path):
    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir()
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    archive.touch()
    manager.cycles_dir.mkdir()
    extracted = manager.cycles_dir / "2026-08-06"
    extracted.mkdir()

    both = manager.remove(date(2026, 8, 6))
    assert (both.removed_archive, both.removed_extracted) == (True, True)
    assert both.removed_anything is True

    neither = manager.remove(date(2026, 8, 6))
    assert (neither.removed_archive, neither.removed_extracted) == (False, False)
    assert neither.removed_anything is False


def _duckdb_cycle_archive(path: Path) -> Path:
    archive = path / "28DaySubscription_Effective_2026-08-06.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("CSV_Data/APT_BASE.csv", "ARPT_ID\nATL\n")
    return archive


def test_duckdb_path_requires_an_exact_iso_cycle(tmp_path):
    manager = CycleManager(tmp_path)

    assert manager.duckdb_path("2026-08-06") == (
        tmp_path / "cycles" / "2026-08-06" / "nasr.duckdb"
    )
    assert manager.duckdb_path(date(2026, 8, 6)).name == "nasr.duckdb"
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        manager.duckdb_path("2026-8-6")


def test_build_duckdb_requires_the_requested_cycle_and_is_idempotent(tmp_path):
    manager = CycleManager(tmp_path / "cache")
    archive = _duckdb_cycle_archive(tmp_path)
    manager.import_archive(archive)

    first = manager.build_duckdb("2026-08-06")
    database = manager.duckdb_path("2026-08-06")
    original_bytes = database.read_bytes()
    original_mtime = database.stat().st_mtime_ns
    second = manager.build_duckdb("2026-08-06")

    assert first.database_path == database
    assert second.database_path == database
    assert database.read_bytes() == original_bytes
    assert database.stat().st_mtime_ns == original_mtime
    with pytest.raises(CycleNotFoundError, match="2026-08-07"):
        manager.build_duckdb("2026-08-07")


def test_build_duckdb_rebuilds_when_extracted_source_is_stale(tmp_path):
    manager = CycleManager(tmp_path / "cache")
    manager.import_archive(_duckdb_cycle_archive(tmp_path))
    first = manager.build_duckdb("2026-08-06")
    database = manager.duckdb_path("2026-08-06")
    source = database.parent / "CSV_Data" / "APT_BASE.csv"
    source.write_text("ARPT_ID\nBWI\n", encoding="utf-8")
    newer = database.stat().st_mtime_ns + 1_000_000
    os.utime(source, ns=(newer, newer))

    second = manager.build_duckdb("2026-08-06")

    assert second.metadata.database_sha256 != first.metadata.database_sha256


def test_remove_can_select_the_duckdb_derivative_without_source_removal(tmp_path):
    manager = CycleManager(tmp_path / "cache")
    manager.import_archive(_duckdb_cycle_archive(tmp_path))
    manager.build_duckdb("2026-08-06")
    database = manager.duckdb_path("2026-08-06")
    metadata = database.with_name("nasr.duckdb.json")
    extracted = database.parent

    result = manager.remove("2026-08-06", archive=False, extracted=False, duckdb=True)

    assert result.removed_duckdb is True
    assert result.removed_anything is True
    assert not database.exists()
    assert not metadata.exists()
    assert extracted.is_dir()


def test_remove_extracted_cycle_reports_its_colocated_duckdb_derivative(tmp_path):
    manager = CycleManager(tmp_path / "cache")
    manager.import_archive(_duckdb_cycle_archive(tmp_path))
    manager.build_duckdb("2026-08-06")

    result = manager.remove("2026-08-06", archive=False, extracted=True)

    assert result.removed_extracted is True
    assert result.removed_duckdb is True
    assert not manager.duckdb_path("2026-08-06").exists()


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


def test_csv_source_locator_prefers_faa_csv_data_over_other_nested_archives(tmp_path):
    cycle = tmp_path / "cycle"
    csv_archive = cycle / "CSV_Data" / "subscription.zip"
    csv_archive.parent.mkdir(parents=True)
    with ZipFile(csv_archive, "w") as output:
        output.writestr("APT_BASE.csv", "ARPT_ID\nBWI\n")
    unrelated = cycle / "Additional_Data" / "AIXM" / "airport.zip"
    unrelated.parent.mkdir(parents=True)
    with ZipFile(unrelated, "w") as output:
        output.writestr("airport.xml", "<airport />")

    assert locate_csv_source(cycle) == csv_archive


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


def test_faa_provider_follows_current_landing_link_to_explicit_nfdc_archive():
    calls = []

    class Response:
        def read(self):
            return b'{"effective_date":"2026-08-06","archive_url":"https://example.test/a.zip"}'

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    landing_url = "https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/"
    detail_url = f"{landing_url}2026-08-06/"
    archive_url = (
        "https://nfdc.faa.gov/webContent/28DaySub/"
        "28DaySubscription_Effective_2026-08-06.zip"
    )

    def opener(url, timeout):
        calls.append((url, timeout))
        response = Response()
        if url == landing_url:
            response.read = lambda: (
                b"<h2>Preview</h2><a href='/air_traffic/flight_info/aeronav/"
                b"Aero_Data/NASR_Subscription/2026-09-03/'>Preview</a>"
                b"<h2>Current</h2><a href='/air_traffic/flight_info/aeronav/"
                b"Aero_Data/NASR_Subscription/2026-08-06/'>Current cycle</a>"
            )
        else:
            response.read = lambda: (
                b"<a href='https://nfdc.faa.gov/webContent/28DaySub/"
                b"28DaySubscription_Effective_2026-08-06.zip'>"
                b"Full subscription</a>"
            )
        return response

    cycle = FaaCycleProvider(landing_url, opener).discover()

    assert cycle.effective_date == date(2026, 8, 6)
    assert cycle.archive_url == archive_url
    assert calls == [(landing_url, 2), (detail_url, 2)]


def test_faa_provider_rejects_non_nfdc_or_mismatched_archive_links():
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    landing_url = "https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/"

    def opener(url, timeout):
        if url == landing_url:
            return Response(
                b"<h2>Current</h2><a href='/air_traffic/flight_info/aeronav/"
                b"Aero_Data/NASR_Subscription/2026-08-06/'>Current cycle</a>"
            )
        return Response(
            b"<a href='https://example.test/28DaySubscription_Effective_2026-08-06.zip'>"
            b"Full subscription</a>"
        )

    with pytest.raises(ValueError, match="full-subscription NFDC ZIP"):
        FaaCycleProvider(landing_url, opener).discover()


def test_update_checks_reuse_successful_metadata(tmp_path):
    class Provider:
        def __init__(self):
            self.calls = 0

        def discover(self):
            self.calls += 1
            return RemoteCycle(date(2026, 8, 6), "https://example.test/a.zip")

    provider = Provider()
    manager = CycleManager(tmp_path, provider=provider)
    fresh = manager.check_for_updates()
    reused = manager.check_for_updates()
    forced = manager.check_for_updates(force=True)
    assert (fresh.from_cache, reused.from_cache, forced.from_cache) == (
        False,
        True,
        False,
    )
    assert provider.calls == 2


def test_failed_update_check_does_not_overwrite_successful_metadata(tmp_path):
    class Provider:
        def discover(self):
            return RemoteCycle(date(2026, 8, 6), "https://example.test/a.zip")

    manager = CycleManager(tmp_path, provider=Provider())
    manager.check_for_updates()
    metadata_path = tmp_path / "update-status.json"
    successful = metadata_path.read_text(encoding="utf-8")

    class FailingProvider:
        def discover(self):
            raise OSError("timeout")

    manager.provider = FailingProvider()
    with pytest.raises(DownloadError, match="metadata check failed") as error:
        manager.check_for_updates(force=True)

    assert isinstance(error.value.__cause__, OSError)
    assert metadata_path.read_text(encoding="utf-8") == successful


def test_update_notification_is_concise_and_suppresses_failures(capsys):
    class Manager:
        def check_for_updates(self):
            return type(
                "Status",
                (),
                {"update_available": True, "newest_remote_cycle": date(2026, 8, 6)},
            )()

    assert notify_if_update_available(Manager())
    assert capsys.readouterr().err == (
        "A newer FAA NASR cycle is available: 2026-08-06\n"
    )

    class FailingManager:
        def check_for_updates(self):
            raise OSError("offline")

    assert not notify_if_update_available(FailingManager())


def test_disable_update_check_skips_provider(monkeypatch):
    monkeypatch.setenv("OPENNASR_DISABLE_UPDATE_CHECK", "1")

    class FailingManager:
        def check_for_updates(self):
            raise AssertionError("provider should not be called")

    assert not notify_if_update_available(FailingManager())


def test_update_notification_uses_default_faa_provider(monkeypatch, tmp_path):
    used = []

    class Provider:
        def discover(self):
            used.append(True)
            return RemoteCycle(date(2026, 8, 6), "https://example.test/archive.zip")

    monkeypatch.delenv("OPENNASR_DISABLE_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(cycles, "FaaCycleProvider", Provider)
    monkeypatch.setattr(cycles, "resolve_cache_dir", lambda _: tmp_path)

    assert notify_if_update_available() is True
    assert used == [True]
