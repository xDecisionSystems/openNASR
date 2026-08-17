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
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen
from datetime import date, datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from shutil import copy2, rmtree
from zipfile import ZipFile, is_zipfile

from platformdirs import user_cache_dir

from .exceptions import ArchiveError, CycleNotFoundError, DownloadError
from .duckdb_builder import DuckDbBuildResult, build_duckdb, duckdb_metadata_path
from .duckdb_metadata import read_metadata


APPLICATION_NAME = "openNASR"
CACHE_DIR_ENV_VAR = "OPENNASR_CACHE_DIR"
ARCHIVE_NAME_PATTERN = re.compile(
    r"^28DaySubscription_Effective_(?P<effective_date>\d{4}-\d{2}-\d{2})\.zip$"
)
FAA_NASR_SUBSCRIPTION_URL = (
    "https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/"
)
FAA_LANDING_HOSTS = frozenset({"www.faa.gov"})
FAA_ARCHIVE_HOSTS = frozenset({"nfdc.faa.gov"})


class _CurrentSectionLinkParser(HTMLParser):
    """Collect links in the FAA landing page's current-cycle section only."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self._heading_level: int | None = None
        self._heading_text: list[str] = []
        self._in_current_section = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_level = int(tag[1])
            self._heading_text = []
        elif tag == "a" and self._in_current_section:
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_data(self, data: str) -> None:
        if self._heading_level is not None:
            self._heading_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._heading_level is None or tag != f"h{self._heading_level}":
            return
        heading = " ".join(self._heading_text).strip().casefold()
        if "current" in heading:
            self._in_current_section = True
        elif self._in_current_section:
            self._in_current_section = False
        self._heading_level = None
        self._heading_text = []


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
class RemovalResult:
    """Which locally cached representations of a cycle were actually removed."""

    removed_archive: bool
    removed_extracted: bool
    removed_duckdb: bool = False

    @property
    def removed_anything(self) -> bool:
        return self.removed_archive or self.removed_extracted or self.removed_duckdb


@dataclass(frozen=True)
class UpdateStatus:
    newest_remote_cycle: date
    newest_cached_cycle: date | None
    update_available: bool
    checked_at: datetime
    source_url: str
    from_cache: bool


class FaaCycleProvider:
    """Discover the FAA's currently advertised full NASR subscription.

    Discovery deliberately follows the FAA's public two-page flow: the
    official subscription landing page's *Current* section supplies a dated
    FAA detail page, and that detail page supplies the explicit NFDC ZIP URL.
    It never infers a future cycle from the 28-day cadence or selects Preview
    material.
    """

    def __init__(
        self, landing_url: str = FAA_NASR_SUBSCRIPTION_URL, opener=urlopen
    ) -> None:
        self.landing_url = landing_url
        self.opener = opener

    def discover(self) -> RemoteCycle:
        landing = self._read_text(self.landing_url)
        effective_date, detail_url = self._current_detail(landing)
        detail = self._read_text(detail_url)
        archive_url = self._archive_url(detail, detail_url, effective_date)
        return RemoteCycle(effective_date=effective_date, archive_url=archive_url)

    def _read_text(self, url: str) -> str:
        with self.opener(url, timeout=2) as response:
            return response.read().decode("utf-8")

    def _current_detail(self, landing: str) -> tuple[date, str]:
        parser = _CurrentSectionLinkParser()
        parser.feed(landing)
        for href in parser.links:
            detail_url = urljoin(self.landing_url, href)
            parsed = urlparse(detail_url)
            match = re.search(r"/NASR_Subscription/(\d{4}-\d{2}-\d{2})/?$", parsed.path)
            if (
                parsed.scheme == "https"
                and parsed.hostname in FAA_LANDING_HOSTS
                and match is not None
                and "preview" not in detail_url.casefold()
            ):
                try:
                    return date.fromisoformat(match.group(1)), detail_url
                except ValueError:
                    continue
        raise ValueError(
            "The FAA subscription page did not publish a valid Current NASR cycle link"
        )

    @staticmethod
    def _archive_url(detail: str, detail_url: str, effective_date: date) -> str:
        # A detail page has no Current section; collect every explicit link.
        class DetailLinkParser(HTMLParser):
            def __init__(self) -> None:
                super().__init__(convert_charrefs=True)
                self.links: list[str] = []

            def handle_starttag(self, tag: str, attrs) -> None:
                if tag == "a":
                    href = dict(attrs).get("href")
                    if href:
                        self.links.append(href)

        detail_parser = DetailLinkParser()
        detail_parser.feed(detail)
        expected_name = f"28DaySubscription_Effective_{effective_date.isoformat()}.zip"
        for href in detail_parser.links:
            archive_url = urljoin(detail_url, href)
            parsed = urlparse(archive_url)
            if (
                parsed.scheme == "https"
                and parsed.hostname in FAA_ARCHIVE_HOSTS
                and Path(parsed.path).name == expected_name
                and "/webContent/28DaySub/" in parsed.path
            ):
                return archive_url
        raise ValueError(
            "The FAA cycle detail page did not publish the expected "
            "full-subscription NFDC ZIP"
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
    csv_directories = sorted(path for path in root.rglob("CSV_Data") if path.is_dir())
    for directory in csv_directories:
        csv_files = sorted(directory.rglob("*.csv"))
        if csv_files:
            return csv_files[0].parent
    for directory in csv_directories:
        archives = sorted(path for path in directory.rglob("*.zip") if is_zipfile(path))
        if archives:
            return archives[0]
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
        status = (
            manager or CycleManager(provider=FaaCycleProvider())
        ).check_for_updates()
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

    @staticmethod
    def _coerce_exact_date(value: str | date) -> date:
        """Normalize a cycle while rejecting non-canonical ISO strings."""

        if isinstance(value, datetime):
            raise ValueError(
                "NASR cycle must be a date or canonical YYYY-MM-DD string"
            )
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            raise ValueError(
                "NASR cycle must be a date or canonical YYYY-MM-DD string"
            )
        try:
            result = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                f"Invalid NASR cycle date {value!r}; expected YYYY-MM-DD."
            ) from error
        if result.isoformat() != value:
            raise ValueError(
                f"Invalid NASR cycle date {value!r}; expected canonical YYYY-MM-DD."
            )
        return result

    def duckdb_path(self, cycle: str | date) -> Path:
        """Return the database path belonging to one exact effective cycle."""

        effective_date = self._coerce_exact_date(cycle)
        return self.cycles_dir / effective_date.isoformat() / "nasr.duckdb"

    def build_duckdb(self, cycle: str | date) -> DuckDbBuildResult:
        """Build or reuse the DuckDB derivative for one exact cached cycle.

        An archive-only cycle is extracted as part of this operation.  No
        neighboring cycle is considered, and an absent exact cycle raises
        :class:`CycleNotFoundError` rather than downloading or selecting a
        fallback.
        """

        effective_date = self._coerce_exact_date(cycle)
        cached = self.get(effective_date)
        if cached is None:
            raise CycleNotFoundError(
                f"No NASR cycle found for requested date {effective_date} in "
                f"{self.cache_dir}."
            )
        if cached.data_path is None:
            if cached.archive_path is None:
                raise CycleNotFoundError(
                    f"No archive or extracted data found for requested date "
                    f"{effective_date} in {self.cache_dir}."
                )
            cached = self.extract_archive(cached.archive_path)
        assert cached.data_path is not None

        source = self._resolve_csv_source(cached.data_path)
        database = self.duckdb_path(effective_date)
        metadata_path = duckdb_metadata_path(database)
        if self._is_current_duckdb_artifact(
            database, metadata_path, effective_date, source
        ):
            metadata = read_metadata(metadata_path, effective_date=effective_date)
            return DuckDbBuildResult(database, metadata_path, metadata)

        archive_sha256 = (
            sha256_file(cached.archive_path)
            if cached.archive_path is not None and cached.archive_path.is_file()
            else None
        )
        return build_duckdb(
            source,
            database,
            effective_date,
            archive_sha256=archive_sha256,
        )

    @staticmethod
    def _is_current_duckdb_artifact(
        database: Path,
        metadata_path: Path,
        effective_date: date,
        source: Path,
    ) -> bool:
        """Return whether a completed derivative can safely be reused."""

        if not database.is_file() or not metadata_path.is_file():
            return False
        try:
            metadata = read_metadata(metadata_path, effective_date=effective_date)
            if sha256_file(database) != metadata.database_sha256:
                return False
            # The sidecar format records the source schema, while source file
            # modification times detect the common case of a changed CSV
            # without requiring a full source read on every API construction.
            return not any(
                path.stat().st_mtime_ns > database.stat().st_mtime_ns
                for path in source.glob("*.csv")
            )
        except (OSError, ValueError):
            return False

    def _resolve_csv_source(self, data_path: Path) -> Path:
        """Resolve CSV directories, extracting nested FAA archives atomically."""

        source = locate_csv_source(data_path)
        if source.is_dir():
            return source
        extracted = source.parent / source.stem
        if extracted.is_dir():
            return self._resolve_csv_source(extracted)
        if extracted.exists():
            raise ArchiveError(f"Cannot extract nested NASR archive over {extracted}")
        temporary = Path(tempfile.mkdtemp(prefix=".nested-", dir=source.parent))
        try:
            with ZipFile(source, "r") as archive:
                for member in archive.infolist():
                    path = PurePosixPath(member.filename)
                    if path.is_absolute() or ".." in path.parts:
                        raise ArchiveError(
                            f"Unsafe archive member: {member.filename}"
                        )
                archive.extractall(temporary)
            locate_csv_source(temporary)
            temporary.replace(extracted)
        except Exception:
            if temporary.exists():
                rmtree(temporary)
            raise
        return self._resolve_csv_source(extracted)

    def available_cycles(self) -> tuple[date, ...]:
        """Return every valid effective date represented in the local cache."""

        archive_dates = {
            effective_date
            for path in self.archive_paths()
            if (effective_date := parse_archive_date(path)) is not None
        }
        extracted_dates = {
            effective_date
            for path in self.extracted_paths()
            if (effective_date := self._extracted_cycle_date(path)) is not None
        }
        return tuple(sorted(archive_dates | extracted_dates))

    def latest(self) -> Cycle:
        """Return the newest cached cycle.

        Raises:
            CycleNotFoundError: If neither archives nor extracted data are cached.
        """

        available = self.available_cycles()
        if not available:
            raise CycleNotFoundError(
                f"No NASR cycles were found in cache directory {self.cache_dir}"
            )
        latest = self.get(available[-1])
        assert latest is not None
        return latest

    @staticmethod
    def _extracted_cycle_date(path: Path) -> date | None:
        """Return the date encoded by a standard extracted-cycle directory."""

        try:
            return date.fromisoformat(path.name)
        except ValueError:
            return None

    def remove(
        self,
        effective_date: str | date,
        *,
        archive: bool = True,
        extracted: bool = True,
        duckdb: bool = False,
    ) -> RemovalResult:
        """Remove selected local representations of an exact cached cycle.

        Returns which representations actually existed and were removed, so
        callers never need to duplicate this method's path construction just
        to report what happened.
        """

        if not archive and not extracted and not duckdb:
            raise ValueError(
                "At least one of archive, extracted, or duckdb must be True"
            )

        effective_date = self._coerce_exact_date(effective_date)

        archive_path = self.archives_dir / (
            f"28DaySubscription_Effective_{effective_date}.zip"
        )
        removed_archive = False
        if archive and archive_path.is_file():
            archive_path.unlink()
            removed_archive = True
        removed_duckdb = False
        if duckdb:
            database_path = self.duckdb_path(effective_date)
            metadata_path = duckdb_metadata_path(database_path)
            if database_path.is_file():
                database_path.unlink()
                removed_duckdb = True
            if metadata_path.is_file():
                metadata_path.unlink()
                removed_duckdb = True
        data_path = self.cycles_dir / effective_date.isoformat()
        removed_extracted = False
        if extracted and data_path.is_dir():
            rmtree(data_path)
            removed_extracted = True
        return RemovalResult(
            removed_archive=removed_archive,
            removed_extracted=removed_extracted,
            removed_duckdb=removed_duckdb,
        )

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
    "FAA_NASR_SUBSCRIPTION_URL",
    "parse_archive_date",
    "locate_csv_source",
    "notify_if_update_available",
    "read_cycle_date",
    "RemoteCycle",
    "RemovalResult",
    "UpdateStatus",
    "resolve_cache_dir",
    "sha256_file",
    "validate_archive",
]
