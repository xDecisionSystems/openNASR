"""Local cache of validated cycles, fetched from the bucket, loaded lazily."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import logging
from pathlib import Path
import threading

from openNASR.exceptions import TableNotFoundError
from openNASR.flightplan import RouteResolver
from openNASR.nasr import NASR
from openNASR_contract import Bucket, FetchError, Manifest, fetch_build, list_builds
from openNASR_contract.fetch import (
    CLASS_AIRSPACE_NAME,
    DATABASE_NAME,
    MANIFEST_NAME,
    SIDECAR_NAME,
)

from .airspace import AirspaceIndex
from .map_layers import LayerName, MapLayer

LOGGER = logging.getLogger("openNASR_api")


class CycleUnavailableError(LookupError):
    """Raised when no usable cycle matches a request."""


def _empty_boundaries():
    from pandas import DataFrame

    return (
        DataFrame(columns=["LOCATION_ID", "LOCATION_NAME"]),
        DataFrame(
            columns=[
                "LOCATION_ID",
                "ALTITUDE",
                "TYPE",
                "POINT_SEQ",
                "LAT_DECIMAL",
                "LONG_DECIMAL",
            ]
        ),
    )


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
        self._lookups: dict[str, NASR] = {}
        self._lookup_locks: dict[str, threading.Lock] = {}
        self._airspace: dict[str, AirspaceIndex] = {}
        self._map_layers: OrderedDict[tuple[str, LayerName], MapLayer] = OrderedDict()
        self._lock = threading.Lock()
        self._refresh_lock = threading.Lock()

    def _directory(self, effective_date: str) -> Path:
        return self.cache_dir / "cycles" / effective_date

    def refresh(self) -> RefreshReport:
        """Fetch new builds and repair incomplete cached builds."""

        report = RefreshReport()
        if self.bucket is None:
            return report
        with self._refresh_lock:
            try:
                builds = list_builds(self.bucket)
            except Exception as error:
                LOGGER.error("could not list validated builds: %s", error)
                report.failed["bucket"] = str(error)
                return report

            newest = {
                manifest.effective_date: manifest
                for manifest in builds
                if manifest.procedure_order == "flight_order"
            }
            for effective_date, manifest in newest.items():
                directory = self._directory(effective_date)
                if (
                    self.manifest(effective_date) == manifest
                    and self._has_artifacts(directory)
                    and (
                        manifest.class_airspace is None
                        or (directory / CLASS_AIRSPACE_NAME).is_file()
                    )
                ):
                    continue
                try:
                    fetch_build(
                        self.bucket,
                        manifest,
                        directory,
                        publication=self._publication(effective_date),
                    )
                    report.fetched.append(effective_date)
                except (FetchError, OSError, ValueError) as error:
                    LOGGER.error("could not fetch cycle %s: %s", effective_date, error)
                    report.failed[effective_date] = str(error)
        return report

    @contextmanager
    def _publication(self, effective_date: str) -> Iterator[None]:
        with self._lookup_lock(effective_date), self._lock:
            nasr = self._lookups.pop(effective_date, None)
            if nasr is not None:
                # DuckDB shares open databases by path within the process.
                nasr.close()
            yield
            self._loaded.pop(effective_date, None)
            self._airspace.pop(effective_date, None)
            for key in tuple(self._map_layers):
                if key[0] == effective_date:
                    del self._map_layers[key]

    def _lookup_lock(self, effective_date: str) -> threading.Lock:
        with self._lock:
            return self._lookup_locks.setdefault(effective_date, threading.Lock())

    @staticmethod
    def _has_artifacts(directory: Path) -> bool:
        return (directory / DATABASE_NAME).is_file() and (
            directory / SIDECAR_NAME
        ).is_file()

    def cycles(self) -> list[str]:
        """Effective dates present on disk, oldest first."""

        root = self.cache_dir / "cycles"
        if not root.is_dir():
            return []
        with self._lock:
            return sorted(
                path.name for path in root.iterdir() if self._has_artifacts(path)
            )

    def manifest(self, effective_date: str) -> Manifest | None:
        path = self._directory(effective_date) / MANIFEST_NAME
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
            with closing(NASR(cycle=chosen, cache_dir=self.cache_dir)) as nasr:
                resolver = RouteResolver.from_nasr(nasr)
            self._loaded[chosen] = resolver
            while len(self._loaded) > self.max_loaded:
                self._loaded.popitem(last=False)
            return chosen, resolver

    def airspace(self, effective_date: str | None = None) -> tuple[str, AirspaceIndex]:
        """The boundary and optional class-polygon index for a cycle."""

        chosen = effective_date or self.default_cycle()
        if chosen not in self.cycles():
            raise CycleUnavailableError(f"cycle {chosen} is not available")
        with self._lock:
            index = self._airspace.get(chosen)
            if index is not None:
                return chosen, index
            manifest = self.manifest(chosen)
            path = self._directory(chosen) / CLASS_AIRSPACE_NAME
            class_airspace = (
                path
                if manifest and manifest.class_airspace and path.is_file()
                else None
            )
            with closing(NASR(cycle=chosen, cache_dir=self.cache_dir)) as nasr:
                try:
                    base, segments = nasr["ARB_BASE"], nasr["ARB_SEG"]
                except TableNotFoundError:
                    base, segments = _empty_boundaries()
            index = AirspaceIndex(base, segments, class_airspace)
            self._airspace[chosen] = index
            return chosen, index

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
        with self._lookup_lock(chosen):
            with self._lock:
                nasr = self._lookups.get(chosen)
                if nasr is None:
                    nasr = NASR(cycle=chosen, cache_dir=self.cache_dir)
                    self._lookups[chosen] = nasr
            yield chosen, nasr.query_table

    def map_layer(
        self, layer: LayerName, lat: float, lon: float, effective_date: str | None
    ) -> tuple[str, dict]:
        chosen = effective_date or self.default_cycle()
        key = (chosen, layer)
        with self._lookup_lock(chosen):
            _, airspace = self.airspace(chosen)
            extent = airspace.artcc_extent(lat, lon)
            if extent.is_empty:
                return chosen, {"points": [], "lines": []}
            with self._lock:
                index = self._map_layers.get(key)
                if index is not None:
                    self._map_layers.move_to_end(key)
            if index is None:
                resolver = (
                    self.resolver(chosen)[1]
                    if layer in {"arrivals", "departures"}
                    else None
                )
                with closing(NASR(cycle=chosen, cache_dir=self.cache_dir)) as nasr:
                    index = MapLayer.from_nasr(nasr, layer, resolver)
                with self._lock:
                    self._map_layers[key] = index
                    while len(self._map_layers) > 4 * self.max_loaded:
                        self._map_layers.popitem(last=False)
        return chosen, index.within(extent)

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
