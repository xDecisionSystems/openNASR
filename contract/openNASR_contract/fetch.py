"""Reader side of the contract: choose a validated build and fetch it.

A reader trusts a build only through its manifest, and trusts a downloaded
file only after its SHA-256 matches the manifest. Nothing here writes to the
bucket.
"""

from __future__ import annotations

from collections.abc import Collection
import hashlib
import json
from pathlib import Path
import tempfile

from .bucket import Bucket
from .keys import BucketKeyError, parse_manifest_key
from .manifest import ArtifactRef, Manifest, ManifestError

DATABASE_NAME = "nasr.duckdb"
SIDECAR_NAME = "nasr.duckdb.json"


class FetchError(RuntimeError):
    """Raised when a build cannot be fetched or fails verification."""


def list_builds(bucket: Bucket) -> list[Manifest]:
    """All validated builds in the bucket, oldest cycle first.

    A manifest that cannot be parsed or that disagrees with its own key is
    skipped: one bad object must not hide the good ones.
    """

    builds = []
    for key in bucket.list_keys():
        try:
            expected = parse_manifest_key(key)
            manifest = Manifest.from_json(bucket.get_bytes(key))
        except (BucketKeyError, ManifestError):
            continue
        if manifest.keys().manifest == expected.manifest:
            builds.append(manifest)
    return sorted(builds, key=lambda m: (m.effective_date, m.builder, m.created_at))


def select_build(
    bucket: Bucket,
    *,
    effective_date: str | None = None,
    on_or_before: str | None = None,
    supported_builders: Collection[int] | None = None,
    supported_procedure_orders: Collection[str] = ("flight_order",),
) -> Manifest | None:
    """The newest usable build for a date, or the latest cycle up to a date.

    Within a cycle the highest supported builder number wins. Builds whose
    procedure order this reader does not support are never returned.
    """

    candidates = [
        m
        for m in list_builds(bucket)
        if (supported_builders is None or m.builder in supported_builders)
        and m.procedure_order in supported_procedure_orders
        and (effective_date is None or m.effective_date == effective_date)
        and (on_or_before is None or m.effective_date <= on_or_before)
    ]
    return candidates[-1] if candidates else None


def fetch_build(bucket: Bucket, manifest: Manifest, directory: Path) -> Path:
    """Place a verified ``nasr.duckdb`` and its sidecar in ``directory``."""

    directory.mkdir(parents=True, exist_ok=True)
    _fetch(bucket, manifest.sidecar, directory / SIDECAR_NAME)
    sidecar = json.loads((directory / SIDECAR_NAME).read_text(encoding="utf-8"))
    if (
        sidecar.get("database_sha256") != manifest.duckdb.sha256
        or sidecar.get("effective_date") != manifest.effective_date
    ):
        (directory / SIDECAR_NAME).unlink()
        raise FetchError("the sidecar does not describe the manifest's database")
    return _fetch(bucket, manifest.duckdb, directory / DATABASE_NAME)


def _fetch(bucket: Bucket, ref: ArtifactRef, destination: Path) -> Path:
    if destination.is_file() and _sha256(destination) == ref.sha256:
        return destination
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, prefix=".fetch-", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        bucket.get_file(ref.key, temporary)
        if _sha256(temporary) != ref.sha256:
            raise FetchError(f"{ref.key} does not match its manifest hash")
        temporary.replace(destination)
    except FetchError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as error:
        temporary.unlink(missing_ok=True)
        raise FetchError(f"could not fetch {ref.key}: {error}") from error
    return destination


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
