from datetime import date, datetime, timezone

from openNASR.cli import build_parser
from openNASR.cli import main
from openNASR.cycles import UpdateStatus


def test_cli_exposes_check_command_and_force_option():
    args = build_parser().parse_args(["check", "--force"])

    assert args.command == "check"
    assert args.force


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
    assert "removed: 2026-08-06" in capsys.readouterr().out
