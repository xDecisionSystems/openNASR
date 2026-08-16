"""Command-line entry point for local NASR cycle management."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from enum import IntEnum

from .cycles import CycleManager


class ExitCode(IntEnum):
    SUCCESS = 0
    USAGE_ERROR = 2
    UNAVAILABLE = 3
    VALIDATION_ERROR = 4
    INTERNAL_ERROR = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opennasr")
    subcommands = parser.add_subparsers(dest="command", required=True)
    check = subcommands.add_parser("check", help="check cached and remote cycles")
    check.add_argument("--force", action="store_true", help="refresh metadata")
    download = subcommands.add_parser("download", help="download a NASR cycle")
    download.add_argument("cycle", help="latest or an ISO cycle date")
    subcommands.add_parser("list", help="list cached NASR cycles")
    remove = subcommands.add_parser("remove", help="remove a cached NASR cycle")
    remove.add_argument("cycle", help="ISO cycle date")
    remove.add_argument("--yes", action="store_true", help="skip confirmation")
    return parser


def main(argv: list[str] | None = None, *, manager=None, confirm=input) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check":
        status = (manager or CycleManager()).check_for_updates(force=args.force)
        age = datetime.now(timezone.utc) - status.checked_at
        print(f"remote: {status.newest_remote_cycle}")
        print(f"cached: {status.newest_cached_cycle or 'none'}")
        print(f"cache age: {int(age.total_seconds())}s")
        print(f"update available: {'yes' if status.update_available else 'no'}")
    elif args.command == "download":
        active_manager = manager or CycleManager()
        if args.cycle == "latest":
            cycle = active_manager.download_latest()
        else:
            cycle = active_manager.download(date.fromisoformat(args.cycle))
        print(f"downloaded: {cycle.effective_date}")
    elif args.command == "list":
        active_manager = manager or CycleManager()
        for archive in active_manager.archive_paths():
            print(f"archive {archive.name} {archive.stat().st_size} {archive}")
        for cycle_path in active_manager.extracted_paths():
            print(f"extracted {cycle_path.name} {cycle_path}")
    elif args.command == "remove":
        active_manager = manager or CycleManager()
        effective_date = date.fromisoformat(args.cycle)
        confirmed = args.yes or (
            confirm(f"Remove cached cycle {effective_date}? [y/N] ").lower() == "y"
        )
        if not confirmed:
            return ExitCode.SUCCESS
        active_manager.remove(effective_date)
        print(f"removed: {effective_date}")
    return ExitCode.SUCCESS
