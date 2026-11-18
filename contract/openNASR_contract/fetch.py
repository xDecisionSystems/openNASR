"""Reader side of the contract: choose a validated build and fetch it.

A reader trusts a build only through its manifest, and trusts a downloaded
file only after its SHA-256 matches the manifest. Nothing here writes to the
bucket.
"""

from __future__ import annotations

from collections.abc import Collection
from contextlib import AbstractContextManager, nullcontext
import hashlib
import json
from pathlib import Path
import tempfile

from .bucket import Bucket
from .keys import BucketKeyError, parse_manifest_key
from .manifest import ArtifactRef, Manifest, ManifestError

DATABASE_NAME = "nasr.duckdb"
SIDECAR_NAME = "nasr.duckdb.json"
MANIFEST_NAME = "manifest.json"
CLASS_AIRSPACE_NAME = "class_airspace.parquet"


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


def fetch_build(
    bucket: Bucket,
    manifest: Manifest,
    directory: Path,
    *,
    publication: AbstractContextManager[None] | None = None,
) -> Path:
    """Verify a complete build before replacing the cached files.

    A live reader can supply a context manager to coordinate publication with
    opening the cached build. Downloads and verification run outside it.
    """

    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory, prefix=".fetch-") as temporary:
        staged = Path(temporary)
        _stage(bucket, manifest.sidecar, directory / SIDECAR_NAME, staged)
        try:
            sidecar = json.loads((staged / SIDECAR_NAME).read_text(encoding="utf-8"))
        except ValueError as error:
            raise FetchError("the sidecar is not valid JSON") from error
        if (
            not isinstance(sidecar, dict)
            or sidecar.get("database_sha256") != manifest.duckdb.sha256
            or sidecar.get("effective_date") != manifest.effective_date
        ):
            raise FetchError("the sidecar does not describe the manifest's database")
        _stage(bucket, manifest.duckdb, directory / DATABASE_NAME, staged)
        if manifest.class_airspace is not None:
            _stage(
                bucket,
                manifest.class_airspace.parquet,
                directory / CLASS_AIRSPACE_NAME,
                staged,
            )
        (staged / MANIFEST_NAME).write_text(manifest.to_json(), encoding="utf-8")

        with publication if publication is not None else nullcontext():
            _publish(staged, directory)
    return directory / DATABASE_NAME


def _stage(bucket: Bucket, ref: ArtifactRef, cached: Path, directory: Path) -> None:
    temporary = directory / cached.name
    try:
        temporary.hardlink_to(cached)
    except FileNotFoundError:
        pass
    else:
        if _sha256(temporary) == ref.sha256:
            return
        temporary.unlink()
    try:
        bucket.get_file(ref.key, temporary)
        if _sha256(temporary) != ref.sha256:
            raise FetchError(f"{ref.key} does not match its manifest hash")
    except FetchError:
        raise
    except Exception as error:
        raise FetchError(f"could not fetch {ref.key}: {error}") from error


def _publish(staged: Path, directory: Path) -> None:
    names = tuple(
        name
        for name in (DATABASE_NAME, SIDECAR_NAME, CLASS_AIRSPACE_NAME, MANIFEST_NAME)
        if (staged / name).exists()
    )
    previous = staged / "previous"
    previous.mkdir()
    for name in names:
        try:
            (previous / name).hardlink_to(directory / name)
        except FileNotFoundError:
            pass

    installed = []
    try:
        for name in names:
            (staged / name).replace(directory / name)
            installed.append(name)
    except OSError:
        for name in reversed(installed):
            backup = previous / name
            if backup.exists():
                backup.replace(directory / name)
            else:
                (directory / name).unlink()
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
