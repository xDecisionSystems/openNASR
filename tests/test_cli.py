from datetime import date, datetime, timezone

from openNASR.cli import build_parser
from openNASR.cli import ExitCode
from openNASR.cli import main
from openNASR.cycles import UpdateStatus
from openNASR.exceptions import DownloadError


def test_cli_exposes_check_command_and_force_option():
    args = build_parser().parse_args(["check", "--force"])

    assert args.command == "check"
    assert args.force


def test_cli_exit_codes_are_stable():
    assert ExitCode.SUCCESS == 0
    assert ExitCode.USAGE_ERROR == 2
    assert ExitCode.UNAVAILABLE == 3
    assert ExitCode.VALIDATION_ERROR == 4
    assert ExitCode.INTERNAL_ERROR == 5


def test_check_reports_cycle_status(capsys):
    class Manager:
        def check_for_updates(self, *, force):
            assert force
            return UpdateStatus(
                date(2026, 9, 3),
                date(2026, 8, 6),
                True,
                datetime.now(timezone.utc),
                "https://example.test/archive.zip",
                False,
            )

    assert main(["check", "--force"], manager=Manager()) == 0
    output = capsys.readouterr().out
    assert "remote: 2026-09-03" in output
    assert "cached: 2026-08-06" in output
    assert "cache age:" in output
    assert "update available: yes" in output


def test_download_commands_delegate_to_cycle_manager(capsys):
    class Manager:
        def download_latest(self):
            return type("Cycle", (), {"effective_date": date(2026, 9, 3)})()

        def download(self, effective_date):
            return type("Cycle", (), {"effective_date": effective_date})()

    manager = Manager()
    assert main(["download", "latest"], manager=manager) == 0
    assert "downloaded: 2026-09-03" in capsys.readouterr().out
    assert main(["download", "2026-08-06"], manager=manager) == 0
    assert "downloaded: 2026-08-06" in capsys.readouterr().out


def test_build_duckdb_commands_delegate_exact_and_latest_cycles(capsys):
    class Manager:
        def __init__(self):
            self.built = []

        def latest(self):
            return type("Cycle", (), {"effective_date": date(2026, 9, 3)})()

        def build_duckdb(self, effective_date):
            self.built.append(effective_date)
            return type(
                "BuildResult",
                (),
                {"database_path": "/tmp/cycles/nasr.duckdb"},
            )()

    manager = Manager()
    assert main(["build-duckdb", "latest"], manager=manager) == 0
    assert main(["build-duckdb", "2026-08-06"], manager=manager) == 0
    assert manager.built == [date(2026, 9, 3), date(2026, 8, 6)]
    assert capsys.readouterr().out.count("ready") == 2


def test_list_storage_reports_duckdb_artifact_state(tmp_path, capsys):
    from openNASR.cycles import CycleManager

    manager = CycleManager(tmp_path)
    manager.cycles_dir.mkdir()
    (manager.cycles_dir / "2026-08-06").mkdir()

    assert main(["list", "--storage"], manager=manager) == 0
    output = capsys.readouterr().out
    assert "duckdb 2026-08-06 absent" in output

    database = manager.duckdb_path("2026-08-06")
    database.write_bytes(b"database")
    database.with_name("nasr.duckdb.json").write_text("{}")
    assert main(["list", "--storage"], manager=manager) == 0
    assert "duckdb 2026-08-06 ready" in capsys.readouterr().out


def test_default_check_and_download_use_a_provider_and_report_typed_errors(
    monkeypatch, capsys, tmp_path
):
    class Provider:
        def __init__(self):
            self.used = True

        def discover(self):
            raise OSError("offline")

    monkeypatch.setattr("openNASR.cli.FaaCycleProvider", Provider)
    monkeypatch.setattr("openNASR.cycles.resolve_cache_dir", lambda _cache: tmp_path)

    assert main(["check", "--force"]) == ExitCode.UNAVAILABLE
    assert main(["download", "latest"]) == ExitCode.UNAVAILABLE
    error = capsys.readouterr().err
    assert "FAA cycle metadata check failed" in error
    assert "Traceback" not in error


def test_cli_maps_configuration_and_validation_errors_without_tracebacks(capsys):
    class ConfigurationManager:
        def check_for_updates(self, *, force):
            raise ValueError("provider configuration is invalid")

    class ValidationManager:
        def check_for_updates(self, *, force):
            raise DownloadError("archive unavailable")

    assert main(["check"], manager=ConfigurationManager()) == ExitCode.USAGE_ERROR
    assert main(["check"], manager=ValidationManager()) == ExitCode.UNAVAILABLE
    error = capsys.readouterr().err
    assert "Traceback" not in error


def test_list_reports_cached_archive_and_extracted_cycle(tmp_path, capsys):
    from openNASR.cycles import CycleManager

    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir()
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    archive.write_bytes(b"data")
    manager.cycles_dir.mkdir()
    (manager.cycles_dir / "2026-08-06").mkdir()

    assert main(["list"], manager=manager) == 0
    output = capsys.readouterr().out
    assert "archive 28DaySubscription_Effective_2026-08-06.zip 4" in output
    assert "extracted 2026-08-06" in output


def test_remove_requires_confirmation_unless_yes(tmp_path, capsys):
    from openNASR.cycles import CycleManager

    manager = CycleManager(tmp_path)
    manager.archives_dir.mkdir()
    archive = manager.archives_dir / "28DaySubscription_Effective_2026-08-06.zip"
    archive.write_bytes(b"data")
    main(["remove", "2026-08-06"], manager=manager, confirm=lambda _: "n")
    assert archive.exists()
    main(["remove", "2026-08-06", "--yes"], manager=manager)
    assert not archive.exists()
    assert "removed archive: 2026-08-06" in capsys.readouterr().out


def test_remove_reports_each_cached_representation_that_was_removed(tmp_path, capsys):
    from openNASR.cycles import CycleManager

    manager = CycleManager(tmp_path)
    manager.cycles_dir.mkdir()
    extracted = manager.cycles_dir / "2026-08-06"
    extracted.mkdir()

    assert main(["remove", "2026-08-06", "--yes"], manager=manager) == 0
    assert not extracted.exists()
    assert "removed extracted: 2026-08-06" in capsys.readouterr().out
