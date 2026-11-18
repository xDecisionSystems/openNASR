"""Verify every validated build in the bucket against its manifest (read-only).

For each build this verifies the DuckDB file, sidecar and optional airspace
Parquet. With ``--zips`` it also verifies the source archives.

    python tools/verify_bucket.py --env-file .env [--cycle 2026-12-24] [--zips]

Exits 1 if any build fails. Uses the read-only API key.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).parents[1]
sys.path[:0] = [str(ROOT / "contract")]

from openNASR_contract import (  # noqa: E402
    Bucket,
    FetchError,
    LocalBucket,
    Manifest,
    fetch_build,
    list_builds,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_build(
    bucket: Bucket,
    manifest: Manifest,
    *,
    check_zip: bool = False,
    work_dir: str | None = None,
) -> list[str]:
    """Return the problems found with one build (empty when it is sound)."""

    label = f"{manifest.effective_date} b{manifest.builder}"
    problems: list[str] = []
    with tempfile.TemporaryDirectory(dir=work_dir) as temporary:
        directory = Path(temporary)
        try:
            fetch_build(bucket, manifest, directory / "cycle")
        except FetchError as error:
            problems.append(f"{label}: {error}")
        if check_zip:
            archive = directory / "archive.zip"
            sources = [("archive", manifest.zip)]
            if manifest.class_airspace is not None:
                sources.append(
                    ("class airspace archive", manifest.class_airspace.source)
                )
            for kind, source in sources:
                try:
                    bucket.get_file(source.key, archive)
                except Exception as error:
                    problems.append(f"{label}: cannot read {source.key}: {error}")
                else:
                    if archive.stat().st_size != source.size:
                        problems.append(
                            f"{label}: {kind} size differs from the manifest"
                        )
                    if _sha256(archive) != source.sha256:
                        problems.append(
                            f"{label}: {kind} hash differs from the manifest"
                        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--local-bucket", type=Path, help="a directory bucket (tests)")
    parser.add_argument("--cycle", help="only this effective date")
    parser.add_argument("--zips", action="store_true", help="also check the archives")
    parser.add_argument("--work-dir", help="scratch directory (default: system temp)")
    args = parser.parse_args(argv)

    if args.local_bucket:
        bucket: Bucket = LocalBucket(args.local_bucket)
    else:
        import os

        from openNASR_contract.s3 import S3Bucket, load_env_file

        environ = dict(os.environ)
        if args.env_file:
            environ = {**load_env_file(args.env_file), **environ}
        bucket = S3Bucket.from_env(environ, "API")

    builds = [m for m in list_builds(bucket) if args.cycle in (None, m.effective_date)]
    if not builds:
        print("no matching builds in the bucket")
        return 1
    failed = False
    for manifest in builds:
        problems = verify_build(
            bucket, manifest, check_zip=args.zips, work_dir=args.work_dir
        )
        failed = failed or bool(problems)
        status = "FAIL" if problems else "ok"
        print(
            f"{status} {manifest.effective_date} b{manifest.builder} "
            f"{manifest.schema_id}"
        )
        for problem in problems:
            print(f"     {problem}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
