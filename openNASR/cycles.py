"""Cycle-cache location helpers.

The cache lives outside the installed package.  Its location is resolved with
the public precedence documented in :mod:`PLAN`: an explicit argument, then
``OPENNASR_CACHE_DIR``, then the platform-specific user cache directory.
"""

from __future__ import annotations

import os
import re
import json
import hashlib
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from zipfile import is_zipfile

from platformdirs import user_cache_dir


APPLICATION_NAME = "openNASR"
CACHE_DIR_ENV_VAR = "OPENNASR_CACHE_DIR"
ARCHIVE_NAME_PATTERN = re.compile(
    r"^28DaySubscription_Effective_(?P<effective_date>\d{4}-\d{2}-\d{2})\.zip$"
)


@dataclass(frozen=True)
class Cycle:
    """A locally known NASR cycle."""

    effective_date: date
    archive_path: Path | None = None
    data_path: Path | None = None
    source_url: str | None = None


def resolve_cache_dir(cache_dir: str | Path | None = None) -> Path:
    """Resolve the cache directory without creating or modifying it."""

    if cache_dir is not None:
        return Path(cache_dir).expanduser()

    configured = os.environ.get(CACHE_DIR_ENV_VAR)
    if configured:
        return Path(configured).expanduser()

    return Path(user_cache_dir(APPLICATION_NAME))


def parse_archive_date(path: str | Path) -> date | None:
    """Return the effective date from a valid FAA archive filename."""

    match = ARCHIVE_NAME_PATTERN.fullmatch(Path(path).name)
    if match is None:
        return None
    try:
        return date.fromisoformat(match["effective_date"])
    except ValueError:
        return None


def read_cycle_date(
    *, archive_path: str | Path | None = None, data_path: str | Path | None = None
) -> date:
    """Read a cycle date from extracted metadata or a validated archive name."""

    if data_path is not None:
        metadata_path = Path(data_path) / "metadata.json"
        if metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            try:
                return date.fromisoformat(metadata["effective_date"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid effective_date in {metadata_path}"
                ) from error

    if archive_path is not None:
        effective_date = parse_archive_date(archive_path)
        if effective_date is not None:
            return effective_date

    raise ValueError("A metadata file or validated NASR archive filename is required")


def sha256_file(path: str | Path) -> str:
    """Compute a file's SHA-256 digest using bounded reads."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_archive(path: str | Path) -> None:
    """Reject HTML responses and files that are not ZIP archives."""

    archive = Path(path)
    prefix = archive.read_bytes()[:512].lstrip().lower()
    if prefix.startswith((b"<!doctype html", b"<html")) or not is_zipfile(archive):
        raise ValueError(f"Invalid NASR archive: {archive}")


class CycleManager:
    """Manage locally cached FAA NASR cycles.

    This initial implementation establishes the cache-location contract; the
    remaining cycle operations are added by the subsequent Milestone 3 tasks.
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = resolve_cache_dir(cache_dir)

    @property
    def archives_dir(self) -> Path:
        """Directory containing imported and downloaded archive files."""

        return self.cache_dir / "archives"

    @property
    def cycles_dir(self) -> Path:
        """Directory containing independently extracted cycle directories."""

        return self.cache_dir / "cycles"

    def archive_paths(self) -> tuple[Path, ...]:
        """Return archive candidates without requiring extracted data."""

        if not self.archives_dir.is_dir():
            return ()
        return tuple(
            sorted(
                (
                    path
                    for path in self.archives_dir.glob("*.zip")
                    if path.is_file() and parse_archive_date(path) is not None
                ),
                key=parse_archive_date,
            )
        )

    def extracted_paths(self) -> tuple[Path, ...]:
        """Return extracted cycle candidates without requiring an archive."""

        if not self.cycles_dir.is_dir():
            return ()
        return tuple(
            sorted(path for path in self.cycles_dir.iterdir() if path.is_dir())
        )

    def import_archive(
        self, path: str | Path, *, expected_cycle: date | None = None
    ) -> Cycle:
        """Copy a validated archive into the cache without altering its source."""

        source = Path(path)
        effective_date = parse_archive_date(source)
        if effective_date is None:
            raise ValueError(f"Invalid NASR archive filename: {source.name}")
        if expected_cycle is not None and effective_date != expected_cycle:
            raise ValueError(
                f"Archive date {effective_date} does not match {expected_cycle}"
            )
        validate_archive(source)
        self.archives_dir.mkdir(parents=True, exist_ok=True)
        destination = self.archives_dir / source.name
        if source.resolve() != destination.resolve():
            copy2(source, destination)
        return Cycle(effective_date=effective_date, archive_path=destination)

    def download_part_path(self, effective_date: date) -> Path:
        """Return the temporary cache path reserved for a cycle download."""

        downloads_dir = self.cache_dir / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir / (
            f"28DaySubscription_Effective_{effective_date.isoformat()}.zip.part"
        )

    def write_download_part(self, effective_date: date, chunks) -> Path:
        """Stream byte chunks to the temporary download path."""

        part_path = self.download_part_path(effective_date)
        with part_path.open("wb") as output:
            for chunk in chunks:
                output.write(chunk)
        return part_path

    def publish_download(self, effective_date: date) -> Cycle:
        """Atomically move a completed temporary download into the archive cache."""

        part_path = self.download_part_path(effective_date)
        destination = self.archives_dir / (
            f"28DaySubscription_Effective_{effective_date.isoformat()}.zip"
        )
        self.archives_dir.mkdir(parents=True, exist_ok=True)
        part_path.replace(destination)
        return Cycle(effective_date=effective_date, archive_path=destination)

    def store_sha256_metadata(self, archive_path: str | Path) -> Path:
        """Write a JSON sidecar containing the archive's SHA-256 digest."""

        archive = Path(archive_path)
        metadata_path = archive.with_name(f"{archive.name}.json")
        metadata_path.write_text(
            json.dumps({"sha256": sha256_file(archive)}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return metadata_path


__all__ = [
    "CACHE_DIR_ENV_VAR",
    "Cycle",
    "CycleManager",
    "parse_archive_date",
    "read_cycle_date",
    "resolve_cache_dir",
    "sha256_file",
    "validate_archive",
]
