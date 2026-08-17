"""Command-line entry point for local NASR cycle management."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from enum import IntEnum

from .cycles import CycleManager, FaaCycleProvider
from .exceptions import ArchiveError, DownloadError, OpenNASRError


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
    list_command = subcommands.add_parser("list", help="list cached NASR cycles")
    list_command.add_argument(
        "--storage",
        action="store_true",
        help="also report per-cycle DuckDB artifact state",
    )
    build_duckdb = subcommands.add_parser(
        "build-duckdb", help="build the DuckDB derivative for a cached cycle"
    )
    build_duckdb.add_argument("cycle", help="latest or an exact ISO cycle date")
    remove = subcommands.add_parser("remove", help="remove a cached NASR cycle")
    remove.add_argument("cycle", help="ISO cycle date")
    remove.add_argument("--yes", action="store_true", help="skip confirmation")
    return parser


def main(argv: list[str] | None = None, *, manager=None, confirm=input) -> int:
    args = build_parser().parse_args(argv)
    try:
        active_manager = manager or CycleManager(provider=FaaCycleProvider())
        if args.command == "check":
            status = active_manager.check_for_updates(force=args.force)
            age = datetime.now(timezone.utc) - status.checked_at
            print(f"remote: {status.newest_remote_cycle}")
            print(f"cached: {status.newest_cached_cycle or 'none'}")
            print(f"cache age: {int(age.total_seconds())}s")
            print(f"update available: {'yes' if status.update_available else 'no'}")
        elif args.command == "download":
            if args.cycle == "latest":
                cycle = active_manager.download_latest()
            else:
                cycle = active_manager.download(date.fromisoformat(args.cycle))
            print(f"downloaded: {cycle.effective_date}")
        elif args.command == "list":
            for archive in active_manager.archive_paths():
                print(f"archive {archive.name} {archive.stat().st_size} {archive}")
            for cycle_path in active_manager.extracted_paths():
                print(f"extracted {cycle_path.name} {cycle_path}")
            if args.storage:
                for effective_date in active_manager.available_cycles():
                    database = active_manager.duckdb_path(effective_date)
                    sidecar = database.with_name(f"{database.name}.json")
                    state = (
                        "ready"
                        if database.is_file() and sidecar.is_file()
                        else "absent"
                    )
                    print(f"duckdb {effective_date} {state} {database}")
        elif args.command == "build-duckdb":
            if args.cycle == "latest":
                effective_date = active_manager.latest().effective_date
            else:
                effective_date = date.fromisoformat(args.cycle)
            result = active_manager.build_duckdb(effective_date)
            print(f"duckdb {effective_date} ready {result.database_path}")
        elif args.command == "remove":
            effective_date = date.fromisoformat(args.cycle)
            confirmed = args.yes or (
                confirm(f"Remove cached cycle {effective_date}? [y/N] ").lower() == "y"
            )
            if not confirmed:
                return ExitCode.SUCCESS
            result = active_manager.remove(effective_date)
            if result.removed_archive:
                print(f"removed archive: {effective_date}")
            if result.removed_extracted:
                print(f"removed extracted: {effective_date}")
            if not result.removed_anything:
                print(f"no cached data found: {effective_date}")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    except (DownloadError, ArchiveError) as error:
        print(f"error: {error}", file=sys.stderr)
        return ExitCode.UNAVAILABLE
    except OpenNASRError as error:
        print(f"error: {error}", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return ExitCode.INTERNAL_ERROR
    return ExitCode.SUCCESS
