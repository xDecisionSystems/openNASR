"""Command-line entry point for local NASR cycle management."""

from __future__ import annotations

import argparse

from .cycles import CycleManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opennasr")
    subcommands = parser.add_subparsers(dest="command", required=True)
    check = subcommands.add_parser("check", help="check cached and remote cycles")
    check.add_argument("--force", action="store_true", help="refresh metadata")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check":
        status = CycleManager().check_for_updates(force=args.force)
        print(f"remote: {status.newest_remote_cycle}")
        print(f"cached: {status.newest_cached_cycle or 'none'}")
        print(f"update available: {'yes' if status.update_available else 'no'}")
    return 0
