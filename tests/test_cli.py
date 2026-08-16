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
