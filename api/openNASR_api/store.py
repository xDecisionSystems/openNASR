"""Local cache of validated cycles, fetched from the bucket, loaded lazily."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import logging
from pathlib import Path
import threading

from openNASR.flightplan import RouteResolver
from openNASR.nasr import NASR
from openNASR_contract import Bucket, FetchError, Manifest, fetch_build, select_build
from openNASR_contract.fetch import list_builds

LOGGER = logging.getLogger("openNASR_api")

ROUTE_TABLES = (
    "APT_BASE",
    "FIX_BASE",
    "NAV_BASE",
    "AWY_BASE",
    "AWY_SEG_ALT",
    "DP_BASE",
    "DP_RTE",
    "DP_APT",
    "STAR_BASE",
    "STAR_RTE",
    "STAR_APT",
)
"""The only tables route resolution reads; others are never loaded."""


class CycleUnavailableError(LookupError):
    """Raised when no usable cycle matches a request."""


class CycleTables(dict):
    """Tables for one cycle, carrying what the resolver reads off the facade."""

    def __init__(self, tables, effective_date: str, procedure_order: str | None):
        super().__init__(tables)
        self.effective_date = effective_date
        self.procedure_order = procedure_order


@dataclass
class RefreshReport:
    fetched: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


class CycleStore:
    """Serves resolvers for cycles held under ``cache_dir/cycles/<date>/``.

    The bucket is optional: with none, the store serves what is already on
    disk. A failed refresh never removes a working cycle.
    """

    def __init__(
        self,
        cache_dir: Path,
        bucket: Bucket | None = None,
        *,
        max_loaded: int = 3,
        today: Callable[[], date] = lambda: datetime.now(timezone.utc).date(),
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.bucket = bucket
        self.max_loaded = max_loaded
        self._today = today
        self._loaded: OrderedDict[str, RouteResolver] = OrderedDict()
        self._lookups: dict[str, tuple[NASR, threading.Lock]] = {}
        self._lock = threading.Lock()

    def _directory(self, effective_date: str) -> Path:
        return self.cache_dir / "cycles" / effective_date

    def refresh(self) -> RefreshReport:
        """Fetch any validated cycle in the bucket that is not on disk yet."""

        report = RefreshReport()
        if self.bucket is None:
            return report
        newest: dict[str, Manifest] = {}
        for manifest in list_builds(self.bucket):
            newest[manifest.effective_date] = manifest  # list is oldest-first
        for effective_date, manifest in sorted(newest.items()):
            if manifest.procedure_order != "flight_order":
                continue
            if select_build(self.bucket, effective_date=effective_date) is None:
                continue
            directory = self._directory(effective_date)
            try:
                if not (directory / "manifest.json").is_file() or (
                    Manifest.from_json((directory / "manifest.json").read_text())
                    != manifest
                ):
                    fetch_build(self.bucket, manifest, directory)
                    (directory / "manifest.json").write_text(
                        manifest.to_json(), encoding="utf-8"
                    )
                    self._forget(effective_date)
                    report.fetched.append(effective_date)
            except (FetchError, OSError, ValueError) as error:
                LOGGER.error("could not fetch cycle %s: %s", effective_date, error)
                report.failed[effective_date] = str(error)
        return report

    def _forget(self, effective_date: str) -> None:
        with self._lock:
            self._loaded.pop(effective_date, None)
            entry = self._lookups.pop(effective_date, None)
        if entry is not None:
            with entry[1]:  # wait for in-flight lookups before dropping it
                pass

    def cycles(self) -> list[str]:
        """Effective dates present on disk, oldest first."""

        root = self.cache_dir / "cycles"
        if not root.is_dir():
            return []
        return sorted(
            path.name
            for path in root.iterdir()
            if (path / "nasr.duckdb").is_file()
            and (path / "nasr.duckdb.json").is_file()
        )

    def manifest(self, effective_date: str) -> Manifest | None:
        path = self._directory(effective_date) / "manifest.json"
        try:
            return Manifest.from_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def default_cycle(self) -> str:
        """The newest cycle that is already in effect."""

        today = self._today().isoformat()
        effective = [d for d in self.cycles() if d <= today]
        if not effective:
            raise CycleUnavailableError("no cycle in effect is available")
        return effective[-1]

    def resolver(self, effective_date: str | None = None) -> tuple[str, RouteResolver]:
        chosen = effective_date or self.default_cycle()
        if chosen not in self.cycles():
            raise CycleUnavailableError(f"cycle {chosen} is not available")
        with self._lock:
            resolver = self._loaded.get(chosen)
            if resolver is not None:
                self._loaded.move_to_end(chosen)
                return chosen, resolver
            nasr = NASR(cycle=chosen, cache_dir=self.cache_dir)
            tables = {name: nasr[name] for name in ROUTE_TABLES if name in set(nasr)}
            resolver = RouteResolver(CycleTables(tables, chosen, nasr.procedure_order))
            self._loaded[chosen] = resolver
            while len(self._loaded) > self.max_loaded:
                self._loaded.popitem(last=False)
            return chosen, resolver

    @contextmanager
    def lookup(
        self, effective_date: str | None = None
    ) -> Iterator[tuple[str, Callable]]:
        """Yield ``(cycle, query_table)`` with exclusive use of the cycle's connection.

        A DuckDB connection is not safe across threads, so lookups on one
        cycle take turns; route resolution does not use this connection.
        """

        chosen = effective_date or self.default_cycle()
        if chosen not in self.cycles():
            raise CycleUnavailableError(f"cycle {chosen} is not available")
        with self._lock:
            entry = self._lookups.get(chosen)
            if entry is None:
                entry = (
                    NASR(cycle=chosen, cache_dir=self.cache_dir),
                    threading.Lock(),
                )
                self._lookups[chosen] = entry
        nasr, lock = entry
        with lock:
            yield chosen, nasr.query_table

    def describe(self) -> list[dict]:
        today = self._today().isoformat()
        rows = []
        for effective_date in self.cycles():
            manifest = self.manifest(effective_date)
            rows.append(
                {
                    "effective_date": effective_date,
                    "in_effect": effective_date <= today,
                    "schema_id": manifest.schema_id if manifest else None,
                    "zip_sha256": manifest.zip.sha256 if manifest else None,
                }
            )
        return rows
