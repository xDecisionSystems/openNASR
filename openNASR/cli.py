"""Command-line entry point for local NASR cycle management."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import date, datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any

from .cycles import CycleManager, FaaCycleProvider
from .exceptions import (
    ArchiveError,
    CycleNotFoundError,
    DownloadError,
    OpenNASRError,
)


class ExitCode(IntEnum):
    SUCCESS = 0
    USAGE_ERROR = 2
    UNAVAILABLE = 3
    VALIDATION_ERROR = 4
    INTERNAL_ERROR = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opennasr")
    parser.add_argument(
        "--cache-dir", type=Path, default=None, help="cycle cache (default: per user)"
    )
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
    route = subcommands.add_parser(
        "route", help="resolve a route to latitude/longitude points"
    )
    route.add_argument("text", help="route text, or '-' to read it from stdin")
    route.add_argument(
        "--icao-message", action="store_true", help="the text is an ICAO FPL message"
    )
    route.add_argument("--cycle", help="effective date (default: the cycle in effect)")
    route.add_argument("--max-segment-nm", type=float, help="great-circle densify")
    route.add_argument(
        "--format",
        choices=("json", "geojson", "table"),
        default="json",
        help="json is the same body the HTTP API returns",
    )
    route.add_argument(
        "--strict", action="store_true", help="exit 1 if the route is not complete"
    )
    serve = subcommands.add_parser(
        "serve", help="run the HTTP API locally against the cached cycles"
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument(
        "--api-key",
        action="append",
        default=[],
        help="accepted key (repeatable; default: OPENNASR_API_KEYS, else a new one)",
    )
    serve.add_argument(
        "--no-auth", action="store_true", help="no key needed (loopback only)"
    )
    fetch = subcommands.add_parser(
        "fetch", help="get validated cycles from the bucket (or the FAA if none)"
    )
    fetch.add_argument(
        "cycle", nargs="?", default="latest", help="latest, all or a date"
    )
    fetch.add_argument("--env-file", type=Path, help="KEY=VALUE settings (S3)")
    return parser


def _default_cycle(manager, today: date) -> date:
    in_effect = [d for d in manager.servable_cycles() if d <= today]
    if not in_effect:
        raise CycleNotFoundError(
            f"No NASR cycle in effect is cached in {manager.cache_dir}; "
            "run 'opennasr fetch' or 'opennasr download latest'."
        )
    return in_effect[-1]


def _route(args, manager) -> int:
    from .flightplan import RouteResolver
    from .icaomessage import IcaoMessageError
    from .nasr import NASR
    from .routejson import route_result_to_dict

    text = sys.stdin.read() if args.text == "-" else args.text
    chosen = (
        date.fromisoformat(args.cycle)
        if args.cycle
        else _default_cycle(manager, datetime.now(timezone.utc).date())
    )
    resolver = RouteResolver.from_nasr(
        NASR(cycle=chosen.isoformat(), cache_dir=manager.cache_dir)
    )
    try:
        if args.icao_message:
            extracted, result = resolver.resolve_icao_message(text)
        else:
            extracted, result = None, resolver.resolve(text)
    except IcaoMessageError as error:
        print(f"error: {error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    body = route_result_to_dict(result, extracted, args.max_segment_nm)
    if args.format == "json":
        print(json.dumps(body, indent=2))
    elif args.format == "geojson":
        print(json.dumps(body["geojson"]))
    else:
        for point in body["points"]:
            print(
                f"{point['lat']:10.5f} {point['lon']:11.5f}  {point['segment']:<11} "
                f"{point['kind']:<12} {point['name']:<10} {point['via'] or ''}"
            )
        for note in body["diagnostics"]:
            print(f"[{note['severity']}] {note['code']}: {note['message']}")
    return ExitCode.SUCCESS if (body["complete"] or not args.strict) else 1


def _serve(args, manager) -> int:
    try:
        import uvicorn

        from openNASR_api import CycleStore, create_app
    except ImportError:
        print(
            "error: 'opennasr serve' needs the API package: "
            "pip install openNASR-api (and uvicorn)",
            file=sys.stderr,
        )
        return ExitCode.UNAVAILABLE
    if args.no_auth and args.host not in ("127.0.0.1", "localhost", "::1"):
        print("error: --no-auth is only allowed on a loopback address", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    for effective_date in manager.servable_cycles():
        manager.ensure_duckdb(effective_date)  # build any that are only sources
    keys = args.api_key or [
        k.strip()
        for k in os.environ.get("OPENNASR_API_KEYS", "").split(",")
        if k.strip()
    ]
    if not keys and not args.no_auth:
        keys = [secrets.token_urlsafe(24)]
        print(f"API key for this session: {keys[0]}")
    store = CycleStore(manager.cache_dir)
    print(f"serving cycles {store.cycles()} on http://{args.host}:{args.port}/docs")
    uvicorn.run(
        create_app(store, keys, require_auth=not args.no_auth, rate_limit_per_minute=0),
        host=args.host,
        port=args.port,
        access_log=False,
    )
    return ExitCode.SUCCESS


def _fetch(args, manager) -> int:
    environ = dict(os.environ)
    if args.env_file:
        from openNASR_contract.s3 import load_env_file

        environ = {**load_env_file(args.env_file), **environ}
    if not environ.get("OPENNASR_S3_BUCKET"):
        # No bucket configured: go to the FAA directly, as 'download' does.
        if args.cycle in ("latest", "all"):
            cycle = manager.download_latest()
        else:
            cycle = manager.download(date.fromisoformat(args.cycle))
        print(f"downloaded: {cycle.effective_date}")
        return ExitCode.SUCCESS
    try:
        from openNASR_contract import fetch_build, list_builds
        from openNASR_contract.s3 import S3Bucket
    except ImportError:
        print(
            "error: S3 fetch needs: pip install 'openNASR-contract[s3]'",
            file=sys.stderr,
        )
        return ExitCode.UNAVAILABLE
    bucket = S3Bucket.from_env(environ, "API")
    newest: dict[str, Any] = {}
    for manifest in list_builds(bucket):
        if manifest.procedure_order == "flight_order":
            newest[manifest.effective_date] = manifest
    today = datetime.now(timezone.utc).date().isoformat()
    if args.cycle == "all":
        wanted = sorted(newest)
    elif args.cycle == "latest":
        wanted = [d for d in sorted(newest) if d <= today][-1:]
    else:
        wanted = [args.cycle] if args.cycle in newest else []
    if not wanted:
        print(
            f"error: no validated build for {args.cycle!r} in the bucket",
            file=sys.stderr,
        )
        return ExitCode.UNAVAILABLE
    for effective_date in wanted:
        manifest = newest[effective_date]
        directory = manager.cycles_dir / effective_date
        fetch_build(bucket, manifest, directory)
        (directory / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
        print(f"fetched: {effective_date}")
    return ExitCode.SUCCESS


def main(argv: list[str] | None = None, *, manager=None, confirm=input) -> int:
    args = build_parser().parse_args(argv)
    try:
        active_manager = manager or CycleManager(
            args.cache_dir, provider=FaaCycleProvider()
        )
        if args.command == "route":
            return _route(args, active_manager)
        if args.command == "serve":
            return _serve(args, active_manager)
        if args.command == "fetch":
            return _fetch(args, active_manager)
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
