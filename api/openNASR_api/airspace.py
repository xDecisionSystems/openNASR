"""Point lookups against FAA boundary tables and optional class polygons."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import logging
from pathlib import Path

import duckdb
from numpy import ndarray
from pandas import DataFrame
from shapely import STRtree, from_wkb, transform, unary_union
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

LOGGER = logging.getLogger("openNASR_api")

NOT_COVERED = "Special-use airspace, including MOAs, is not searched."
NO_CLASS_AIRSPACE = "Class B/C/D/E polygons are unavailable for this cycle."


@dataclass(frozen=True)
class AltitudeLimit:
    """Altitude value, unit and reference code as published by the FAA."""

    value: str
    unit: str
    code: str


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    kind: str  # ARTCC | FIR | CTA | UTA | CTA/FIR | CLASS
    level: str  # low | high | unlimited; empty for CLASS
    airspace_class: str | None = None
    local_type: str | None = None
    lower: AltitudeLimit | None = None
    upper: AltitudeLimit | None = None


def _rings(points: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """Split on explicitly closed rings, as the FAA lists disjoint parts."""

    rings, current = [], []
    for point in points:
        current.append(point)
        if len(current) >= 4 and point == current[0]:
            rings.append(current)
            current = []
    if len(current) >= 3:
        rings.append(current + [current[0]])
    return [ring for ring in rings if len(ring) >= 4]


def _polygonal_parts(geometry: BaseGeometry) -> list[Polygon]:
    """Polygons inside ``geometry``; repair can leave stray lines and points."""

    if geometry.geom_type == "Polygon":
        return [] if geometry.is_empty else [geometry]
    parts: list[Polygon] = []
    for child in getattr(geometry, "geoms", []):
        parts.extend(_polygonal_parts(child))
    return parts


def _shift_longitudes(coordinates: ndarray) -> ndarray:
    shifted = coordinates.copy()
    shifted[:, 0] %= 360
    return shifted


class AirspaceIndex:
    """A spatial index over one cycle's boundaries and class polygons."""

    def __init__(
        self, base: DataFrame, segments: DataFrame, class_airspace: Path | None = None
    ) -> None:
        names = {
            str(row["LOCATION_ID"]).strip().upper(): str(row.get("LOCATION_NAME", ""))
            for row in base.to_dict(orient="records")
        }
        self._regions: list[Region] = []
        shapes: dict[bool, list[BaseGeometry]] = {False: [], True: []}
        self._members: dict[bool, list[int]] = {False: [], True: []}
        skipped = 0
        ordered = segments.assign(
            _seq=segments["POINT_SEQ"].map(lambda v: int(str(v) or 0))
        ).sort_values("_seq", kind="stable")
        for (location, altitude, kind), group in ordered.groupby(
            ["LOCATION_ID", "ALTITUDE", "TYPE"], sort=False
        ):
            try:
                points = [
                    (float(lon), float(lat))
                    for lon, lat in zip(group["LONG_DECIMAL"], group["LAT_DECIMAL"])
                ]
            except (TypeError, ValueError):
                skipped += 1
                continue
            if not points:
                skipped += 1
                continue
            lons = [p[0] for p in points]
            wraps = max(lons) - min(lons) > 180
            if wraps:
                # Crosses the antimeridian: shift western longitudes east so the
                # outline is contiguous, and shift the query point the same way.
                points = [(lon + 360 if lon < 0 else lon, lat) for lon, lat in points]
            polygons = [
                part
                for ring in _rings(points)
                for part in _polygonal_parts(make_valid(Polygon(ring)))
            ]
            if not polygons:
                skipped += 1
                continue
            shape = unary_union(polygons)
            ident = str(location).strip().upper()
            self._regions.append(
                Region(
                    id=ident,
                    name=names.get(ident, "").strip(),
                    kind=str(kind).strip().upper(),
                    level=str(altitude).strip().lower(),
                )
            )
            shapes[wraps].append(shape)
            self._members[wraps].append(len(self._regions) - 1)
        if skipped:
            LOGGER.info("airspace index skipped %d unusable boundaries", skipped)
        self.not_covered = NOT_COVERED
        if class_airspace is None:
            self.not_covered += f" {NO_CLASS_AIRSPACE}"
        else:
            for region, geometry in _class_regions(class_airspace):
                self._regions.append(region)
                for part in _polygonal_parts(geometry):
                    west, _, east, _ = part.bounds
                    wraps = east - west > 180
                    shape = transform(part, _shift_longitudes) if wraps else part
                    shapes[wraps].append(shape)
                    self._members[wraps].append(len(self._regions) - 1)
        self._trees = {
            wrapped: STRtree(group) if group else None
            for wrapped, group in shapes.items()
        }

    def __len__(self) -> int:
        return len(self._regions)

    def at(self, lat: float, lon: float) -> list[Region]:
        found: set[int] = set()
        for wrapped, tree in self._trees.items():
            if tree is None:
                continue
            x = lon + 360 if wrapped and lon < 0 else lon
            for hit in tree.query(Point(x, lat), predicate="intersects"):
                found.add(self._members[wrapped][hit])
        regions = (self._regions[index] for index in sorted(found))
        return sorted(regions, key=lambda r: (r.id, r.level, r.kind))


def _class_regions(path: Path) -> Iterator[tuple[Region, BaseGeometry]]:
    with duckdb.connect() as connection:
        rows = connection.execute(
            """
            SELECT IDENT, NAME, CLASS, LOCAL_TYPE, LOWER_VAL, LOWER_UOM, LOWER_CODE,
                   UPPER_VAL, UPPER_UOM, UPPER_CODE, GEOMETRY_WKB
            FROM read_parquet(?)
            """,
            [str(path)],
        ).fetchall()
    for (
        ident,
        name,
        category,
        local_type,
        lower_value,
        lower_unit,
        lower_code,
        upper_value,
        upper_unit,
        upper_code,
        wkb,
    ) in rows:
        yield (
            Region(
                id=ident,
                name=name,
                kind="CLASS",
                level="",
                airspace_class=category,
                local_type=local_type,
                lower=AltitudeLimit(lower_value, lower_unit, lower_code),
                upper=AltitudeLimit(upper_value, upper_unit, upper_code),
            ),
            from_wkb(wkb),
        )
