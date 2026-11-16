"""Command line: ``openNASR-archiver run | status | publish | rebuild``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
import logging
import os
from pathlib import Path
import sys

from openNASR.cycles import CycleManager, FaaCycleProvider
from openNASR_contract import (
    Bucket,
    LocalBucket,
    list_builds,
    select_build,
)

from .publish import PublishError, publish_cycle
from .rebuild import rebuild_from_bucket
from .run import CompositeNotifier, LogNotifier, Notifier, WebhookNotifier, run_once

DEFAULT_CACHE = Path("/var/lib/openNASR-archiver/cache")
DEFAULT_STATE = Path("/var/lib/openNASR-archiver/state.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openNASR-archiver")
    parser.add_argument("--env-file", type=Path, help="KEY=VALUE file with settings")
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--state-file", type=Path, default=None)
    parser.add_argument(
        "--local-bucket",
        type=Path,
        help="use this directory as the bucket instead of S3 (testing)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="one pass: discover, download, publish (timer)")
    commands.add_parser("status", help="list the validated builds in the bucket")
    publish = commands.add_parser("publish", help="publish an already-cached cycle")
    publish.add_argument("date", help="effective date, YYYY-MM-DD")
    rebuild = commands.add_parser(
        "rebuild", help="recreate a database from its archived zip and compare"
    )
    rebuild.add_argument("date", nargs="?", help="effective date (default: newest)")
    return parser


def _environment(arguments) -> dict[str, str]:
    environ = dict(os.environ)
    if arguments.env_file:
        from openNASR_contract.s3 import load_env_file

        environ = {**load_env_file(arguments.env_file), **environ}
    return environ


def _bucket(arguments, environ) -> Bucket:
    if arguments.local_bucket:
        return LocalBucket(arguments.local_bucket)
    from openNASR_contract.s3 import S3Bucket

    return S3Bucket.from_env(environ, "ARCHIVER")


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    arguments = _parser().parse_args(argv)
    environ = _environment(arguments)
    cache = arguments.cache_dir or Path(
        environ.get("OPENNASR_CACHE_DIR", DEFAULT_CACHE)
    )
    state = arguments.state_file or Path(
        environ.get("OPENNASR_STATE_FILE", DEFAULT_STATE)
    )
    try:
        bucket = _bucket(arguments, environ)
    except KeyError as error:
        print(f"error: {error.args[0]}", file=sys.stderr)
        return 2

    if arguments.command == "status":
        builds = list_builds(bucket)
        for build in builds:
            print(
                f"{build.effective_date} b{build.builder} {build.schema_id} "
                f"{build.procedure_order} db={build.duckdb.size} zip={build.zip.size}"
            )
        if not builds:
            print("no validated builds")
        return 0

    if arguments.command == "rebuild":
        manifest = select_build(
            bucket,
            effective_date=arguments.date,
            supported_procedure_orders=("flight_order",),
        )
        if manifest is None:
            print("error: no matching build", file=sys.stderr)
            return 1
        report = rebuild_from_bucket(bucket, manifest, cache)

        def word(matches: bool) -> str:
            return "match" if matches else "DIFFER"

        print(
            f"{report.effective_date}: tables {word(report.tables_match)}, "
            f"schema {word(report.schema_id_match)}, "
            f"fingerprint {word(report.schema_fingerprint_match)}"
        )
        return 0 if report.ok else 1

    if arguments.command == "publish":
        manager = CycleManager(cache)
        try:
            result = publish_cycle(manager, date.fromisoformat(arguments.date), bucket)
        except PublishError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        print("already published" if result.already_published else "published")
        return 0

    notifiers: list[Notifier] = [LogNotifier()]
    if environ.get("OPENNASR_ALERT_WEBHOOK_URL"):
        notifiers.append(WebhookNotifier(environ["OPENNASR_ALERT_WEBHOOK_URL"]))
    manager = CycleManager(cache, provider=FaaCycleProvider())
    outcome = run_once(manager, bucket, state, notifier=CompositeNotifier(*notifiers))
    print(
        f"{outcome.status} {outcome.effective_date or ''} {outcome.kind or ''}".strip()
    )
    return 1 if outcome.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
