"""Cycle-cache location helpers.

The cache lives outside the installed package.  Its location is resolved with
the public precedence documented in :mod:`PLAN`: an explicit argument, then
``OPENNASR_CACHE_DIR``, then the platform-specific user cache directory.
"""

from __future__ import annotations

import os
import re
import json
from datetime import date
from pathlib import Path

from platformdirs import user_cache_dir


APPLICATION_NAME = "openNASR"
CACHE_DIR_ENV_VAR = "OPENNASR_CACHE_DIR"
ARCHIVE_NAME_PATTERN = re.compile(
    r"^28DaySubscription_Effective_(?P<effective_date>\d{4}-\d{2}-\d{2})\.zip$"
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


__all__ = [
    "CACHE_DIR_ENV_VAR",
    "CycleManager",
    "parse_archive_date",
    "read_cycle_date",
    "resolve_cache_dir",
]
