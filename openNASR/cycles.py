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
import tempfile
import sys
from urllib.request import urlopen
from datetime import date, datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from shutil import copy2, rmtree
from zipfile import ZipFile, is_zipfile

from platformdirs import user_cache_dir

from .exceptions import ArchiveError, DownloadError


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


@dataclass(frozen=True)
class RemoteCycle:
    """Metadata for a remotely available FAA cycle."""

    effective_date: date
    archive_url: str


@dataclass(frozen=True)
class UpdateStatus:
    newest_remote_cycle: date
    newest_cached_cycle: date | None
    update_available: bool
    checked_at: datetime
    source_url: str
    from_cache: bool


class FaaCycleProvider:
    """Metadata-only FAA cycle provider with an injectable transport."""

    def __init__(self, metadata_url: str, opener=urlopen) -> None:
        self.metadata_url = metadata_url
        self.opener = opener

    def discover(self) -> RemoteCycle:
        with self.opener(self.metadata_url, timeout=2) as response:
            metadata = json.loads(response.read().decode("utf-8"))
        return RemoteCycle(
            effective_date=date.fromisoformat(metadata["effective_date"]),
            archive_url=metadata["archive_url"],
        )


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


def locate_csv_source(data_path: str | Path) -> Path:
    """Locate a nested CSV directory or FAA CSV archive within a cycle."""

    root = Path(data_path)
    csv_files = sorted(root.rglob("*.csv"))
    if csv_files:
        return csv_files[0].parent
    archives = sorted(path for path in root.rglob("*.zip") if is_zipfile(path))
    if archives:
        return archives[0]
    raise ArchiveError(f"No NASR CSV directory or archive found in {root}")


def notify_if_update_available(manager=None) -> bool:
    """Safely emit one update notice; failures never escape package import."""

    if os.environ.get("OPENNASR_DISABLE_UPDATE_CHECK") == "1":
        return False
    try:
        status = (manager or CycleManager()).check_for_updates()
    except Exception:
        return False
    if status.update_available:
        print(
            f"A newer FAA NASR cycle is available: {status.newest_remote_cycle}",
            file=sys.stderr,
        )
        return True
    return False


class CycleManager:
    """Manage locally cached FAA NASR cycles.

    This initial implementation establishes the cache-location contract; the
    remaining cycle operations are added by the subsequent Milestone 3 tasks.
    """

    def __init__(self, cache_dir: str | Path | None = None, *, provider=None) -> None:
        self.cache_dir = resolve_cache_dir(cache_dir)
        self.provider = provider

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
                key=lambda path: parse_archive_date(path) or date.min,
            )
        )

    def get(self, effective_date: date, *, force: bool = False) -> Cycle | None:
        """Return a valid cached cycle, reusing it unless ``force`` is set."""

        if force:
            return None
        archive = self.archives_dir / (
            f"28DaySubscription_Effective_{effective_date.isoformat()}.zip"
        )
        if archive.is_file() and parse_archive_date(archive) == effective_date:
            validate_archive(archive)
            data_path = self.cycles_dir / effective_date.isoformat()
            return Cycle(
                effective_date=effective_date,
                archive_path=archive,
                data_path=data_path if data_path.is_dir() else None,
            )
        data_path = self.cycles_dir / effective_date.isoformat()
        if data_path.is_dir():
            return Cycle(effective_date=effective_date, data_path=data_path)
        return None

    def remove(self, effective_date: date) -> None:
        """Remove the exact cached archive and extracted cycle when present."""

        archive = self.archives_dir / (
            f"28DaySubscription_Effective_{effective_date}.zip"
        )
        archive.unlink(missing_ok=True)
        data_path = self.cycles_dir / effective_date.isoformat()
        if data_path.is_dir():
            rmtree(data_path)

    def check_for_updates(self, *, force: bool = False) -> UpdateStatus:
        """Return remote-cycle status, reusing successful metadata for 24 hours."""

        metadata_path = self.cache_dir / "update-status.json"
        now = datetime.now(timezone.utc)
        cached = None
        if metadata_path.is_file() and not force:
            cached = json.loads(metadata_path.read_text(encoding="utf-8"))
            checked_at = datetime.fromisoformat(cached["checked_at"])
            if now - checked_at < timedelta(hours=24):
                remote = date.fromisoformat(cached["effective_date"])
                return self._update_status(
                    remote, checked_at, cached["source_url"], True
                )
        if self.provider is None:
            raise ValueError("A FAA cycle provider is required for update checks")
        try:
            remote_cycle = self.provider.discover()
        except Exception as error:
            raise DownloadError("FAA cycle metadata check failed") from error
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(
                {
                    "effective_date": remote_cycle.effective_date.isoformat(),
                    "source_url": remote_cycle.archive_url,
                    "checked_at": now.isoformat(),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return self._update_status(
            remote_cycle.effective_date, now, remote_cycle.archive_url, False
        )

    def _update_status(
        self, remote, checked_at, source_url, from_cache
    ) -> UpdateStatus:
        cached_dates = [
            effective_date
            for path in self.archive_paths()
            if (effective_date := parse_archive_date(path)) is not None
        ]
        newest_cached = max(cached_dates) if cached_dates else None
        return UpdateStatus(
            remote,
            newest_cached,
            newest_cached is None or remote > newest_cached,
            checked_at,
            source_url,
            from_cache,
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
        try:
            with part_path.open("wb") as output:
                for chunk in chunks:
                    output.write(chunk)
        except Exception:
            part_path.unlink(missing_ok=True)
            raise
        return part_path

    def download(self, effective_date: date, *, force: bool = False) -> Cycle:
        """Download the provider's advertised archive for ``effective_date``."""

        cached = self.get(effective_date, force=force)
        if cached is not None:
            return cached
        if self.provider is None:
            raise ValueError("A FAA cycle provider is required for downloads")
        try:
            remote_cycle = self.provider.discover()
            if remote_cycle.effective_date != effective_date:
                raise ValueError(
                    f"Provider does not offer NASR cycle {effective_date.isoformat()}"
                )
            with urlopen(remote_cycle.archive_url, timeout=2) as response:
                part_path = self.write_download_part(
                    effective_date,
                    iter(lambda: response.read(1024 * 1024), b""),
                )
            validate_archive(part_path)
            cycle = self.publish_download(effective_date)
            assert cycle.archive_path is not None
            self.store_sha256_metadata(cycle.archive_path)
            return Cycle(
                effective_date=cycle.effective_date,
                archive_path=cycle.archive_path,
                source_url=remote_cycle.archive_url,
            )
        except Exception as error:
            self.download_part_path(effective_date).unlink(missing_ok=True)
            if isinstance(error, (DownloadError, ValueError)):
                raise
            raise DownloadError(
                f"FAA cycle download failed for {effective_date.isoformat()}"
            ) from error

    def download_latest(self, *, force: bool = False) -> Cycle:
        """Download the latest cycle advertised by the configured provider."""

        status = self.check_for_updates(force=force)
        return self.download(status.newest_remote_cycle, force=force)

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

    def extract_archive(self, archive_path: str | Path) -> Cycle:
        """Safely extract, validate, and atomically publish a cached cycle."""

        archive = Path(archive_path)
        validate_archive(archive)
        effective_date = read_cycle_date(archive_path=archive)
        self.cycles_dir.mkdir(parents=True, exist_ok=True)
        destination = self.cycles_dir / effective_date.isoformat()
        temporary = Path(tempfile.mkdtemp(prefix=".extract-", dir=self.cycles_dir))
        try:
            with ZipFile(archive) as source:
                for member in source.infolist():
                    path = PurePosixPath(member.filename)
                    if path.is_absolute() or ".." in path.parts:
                        raise ArchiveError(f"Unsafe archive member: {member.filename}")
                source.extractall(temporary)
            locate_csv_source(temporary)
            (temporary / "metadata.json").write_text(
                json.dumps({"effective_date": effective_date.isoformat()}) + "\n",
                encoding="utf-8",
            )
            if destination.exists():
                rmtree(temporary)
            else:
                temporary.replace(destination)
            return Cycle(
                effective_date=effective_date,
                archive_path=archive,
                data_path=destination,
            )
        except Exception:
            if temporary.exists():
                rmtree(temporary)
            raise


__all__ = [
    "CACHE_DIR_ENV_VAR",
    "Cycle",
    "CycleManager",
    "FaaCycleProvider",
    "parse_archive_date",
    "locate_csv_source",
    "notify_if_update_available",
    "read_cycle_date",
    "RemoteCycle",
    "UpdateStatus",
    "resolve_cache_dir",
    "sha256_file",
    "validate_archive",
]
