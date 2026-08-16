"""Cycle-cache location helpers.

The cache lives outside the installed package.  Its location is resolved with
the public precedence documented in :mod:`PLAN`: an explicit argument, then
``OPENNASR_CACHE_DIR``, then the platform-specific user cache directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_cache_dir


APPLICATION_NAME = "openNASR"
CACHE_DIR_ENV_VAR = "OPENNASR_CACHE_DIR"


def resolve_cache_dir(cache_dir: str | Path | None = None) -> Path:
    """Resolve the cache directory without creating or modifying it."""

    if cache_dir is not None:
        return Path(cache_dir).expanduser()

    configured = os.environ.get(CACHE_DIR_ENV_VAR)
    if configured:
        return Path(configured).expanduser()

    return Path(user_cache_dir(APPLICATION_NAME))


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
            sorted(path for path in self.archives_dir.glob("*.zip") if path.is_file())
        )

    def extracted_paths(self) -> tuple[Path, ...]:
        """Return extracted cycle candidates without requiring an archive."""

        if not self.cycles_dir.is_dir():
            return ()
        return tuple(
            sorted(path for path in self.cycles_dir.iterdir() if path.is_dir())
        )


__all__ = ["CACHE_DIR_ENV_VAR", "CycleManager", "resolve_cache_dir"]
