"""``openNASR-api serve``: refresh cycles from the bucket and run the server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import logging
import os
from pathlib import Path
import threading

from openNASR_contract import Bucket, LocalBucket

from .app import create_app
from .store import CycleStore

DEFAULT_CACHE = Path("/var/lib/openNASR-api/cache")


def build_store(
    environ: dict[str, str], local_bucket: Path | None = None
) -> CycleStore:
    cache = Path(environ.get("OPENNASR_API_CACHE_DIR", DEFAULT_CACHE))
    bucket: Bucket | None
    if local_bucket is not None:
        bucket = LocalBucket(local_bucket)
    elif environ.get("OPENNASR_S3_BUCKET"):
        from openNASR_contract.s3 import S3Bucket

        bucket = S3Bucket.from_env(environ, "API")
    else:
        bucket = None
    return CycleStore(cache, bucket)


def api_keys(environ: dict[str, str]) -> list[str]:
    return [
        k.strip() for k in environ.get("OPENNASR_API_KEYS", "").split(",") if k.strip()
    ]


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="openNASR-api")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--host", default=None, help="default 127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="default 8000")
    parser.add_argument(
        "--local-bucket", type=Path, help="serve from a directory bucket"
    )
    parser.add_argument(
        "--refresh-minutes",
        type=int,
        default=60,
        help="how often to look for new cycles",
    )
    arguments = parser.parse_args(argv)

    environ = dict(os.environ)
    if arguments.env_file:
        from openNASR_contract.s3 import load_env_file

        environ = {**load_env_file(arguments.env_file), **environ}
    host = arguments.host or environ.get("OPENNASR_API_HOST", "127.0.0.1")
    port = arguments.port or int(environ.get("OPENNASR_API_PORT", "8000"))
    keys = api_keys(environ)
    if not keys:
        print("error: OPENNASR_API_KEYS is not set (comma-separated keys)")
        return 2
    store = build_store(environ, arguments.local_bucket)
    report = store.refresh()
    logging.getLogger("openNASR_api").info(
        "cycles on disk: %s; fetched now: %s", store.cycles(), report.fetched
    )

    def keep_fresh() -> None:
        while not stop.wait(arguments.refresh_minutes * 60):
            store.refresh()

    stop = threading.Event()
    threading.Thread(target=keep_fresh, daemon=True).start()

    import uvicorn

    app = create_app(
        store,
        keys,
        rate_limit_per_minute=int(environ.get("OPENNASR_API_RATE_PER_MINUTE", "120")),
    )
    uvicorn.run(app, host=host, port=port, access_log=False)
    stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
