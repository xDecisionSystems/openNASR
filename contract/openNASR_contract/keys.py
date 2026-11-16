"""Bucket key layout.

::

    <year>/<date>_<zipsha>.zip                  the FAA download (immutable)
    <year>/<date>_<zipsha>.b<N>.duckdb          derived database, builder N
    <year>/<date>_<zipsha>.b<N>.json            manifest, uploaded last

A build is *validated* once and only once its manifest exists, so a reader
that lists manifests never sees a half-published build. Keys contain the
content hash of the zip, so a re-published cycle cannot overwrite one.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

LAYOUT_VERSION = 1

_DATE = r"\d{4}-\d{2}-\d{2}"
_SHA = r"[0-9a-f]{64}"
_MANIFEST_KEY = re.compile(
    rf"^(?P<year>\d{{4}})/(?P<date>{_DATE})_(?P<sha>{_SHA})\.b(?P<builder>[1-9]\d*)\.json$"
)


class BucketKeyError(ValueError):
    """Raised for an invalid effective date, hash, builder number or key."""


@dataclass(frozen=True)
class BuildKeys:
    """The three keys that make up one build of one cycle."""

    effective_date: str
    zip_sha256: str
    builder: int
    zip: str
    duckdb: str
    manifest: str


def build_keys(effective_date: str, zip_sha256: str, builder: int) -> BuildKeys:
    if not re.fullmatch(_DATE, effective_date):
        raise BucketKeyError(f"effective date must be YYYY-MM-DD: {effective_date!r}")
    if not re.fullmatch(_SHA, zip_sha256):
        raise BucketKeyError("zip hash must be 64 lowercase hex characters")
    if isinstance(builder, bool) or not isinstance(builder, int) or builder < 1:
        raise BucketKeyError(f"builder must be a positive integer: {builder!r}")
    stem = f"{effective_date[:4]}/{effective_date}_{zip_sha256}"
    return BuildKeys(
        effective_date=effective_date,
        zip_sha256=zip_sha256,
        builder=builder,
        zip=f"{stem}.zip",
        duckdb=f"{stem}.b{builder}.duckdb",
        manifest=f"{stem}.b{builder}.json",
    )


def parse_manifest_key(key: str) -> BuildKeys:
    """Recover a build's keys from its manifest key (as listed from a bucket)."""

    match = _MANIFEST_KEY.match(key)
    if match is None:
        raise BucketKeyError(f"not a manifest key: {key!r}")
    keys = build_keys(match["date"], match["sha"], int(match["builder"]))
    if match["year"] != match["date"][:4]:
        raise BucketKeyError(f"year folder does not match the date: {key!r}")
    return keys
