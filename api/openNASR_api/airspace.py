"""Point lookups against FAA boundary tables and optional class polygons."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

import duckdb
from numpy import ndarray
from pandas import DataFrame
from shapely import STRtree, clip_by_rect, from_wkb, get_parts, transform, unary_union
from shapely.affinity import translate
from shapely.geometry import Point, Polygon, box
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


def map_coordinates(coordinates: Any) -> list[dict[str, float]]:
    return [{"lon": (x + 180) % 360 - 180, "lat": y} for x, y in coordinates]


def _display_ring(ring: BaseGeometry, tolerance: float) -> list[dict[str, float]]:
    return map_coordinates(ring.simplify(tolerance, preserve_topology=False).coords)


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
        self._artcc: dict[int, BaseGeometry] = {}
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
            if self._regions[-1].kind == "ARTCC":
                self._artcc[len(self._regions) - 1] = shape
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

    def _hits(self, lat: float, lon: float) -> set[int]:
        found: set[int] = set()
        for wrapped, tree in self._trees.items():
            if tree is None:
                continue
            x = lon + 360 if wrapped and lon < 0 else lon
            for hit in tree.query(Point(x, lat), predicate="intersects"):
                found.add(self._members[wrapped][hit])
        return found

    def at(self, lat: float, lon: float) -> list[Region]:
        regions = (self._regions[index] for index in sorted(self._hits(lat, lon)))
        return sorted(regions, key=lambda r: (r.id, r.level, r.kind))

    def boundaries_at(self, lat: float, lon: float) -> list[dict]:
        """Return the polygon components that contain the query point."""
        boundaries = []
        for wrapped, tree in self._trees.items():
            if tree is None:
                continue
            point = Point(lon + 360 if wrapped and lon < 0 else lon, lat)
            for hit in tree.query(point, predicate="intersects"):
                region = self._regions[self._members[wrapped][hit]]
                rings = [
                    _display_ring(
                        ring,
                        max(
                            polygon.bounds[2] - polygon.bounds[0],
                            polygon.bounds[3] - polygon.bounds[1],
                        )
                        / 3000,
                    )
                    for polygon in _polygonal_parts(tree.geometries[hit])
                    if polygon.intersects(point)
                    for ring in (polygon.exterior, *polygon.interiors)
                ]
                boundaries.append(
                    {
                        "id": region.id,
                        "level": region.level,
                        "kind": region.airspace_class or region.kind,
                        "rings": rings,
                    }
                )
        return boundaries

    def boundaries_in_view(
        self, west: float, south: float, span: float, north: float
    ) -> list[dict]:
        """Clip boundary lines to a viewport without adding artificial edges."""
        tolerance = max(span, north - south) / 3000
        boundaries = []
        for wrapped, tree in self._trees.items():
            if tree is None:
                continue
            origin = 0 if wrapped else -180
            start = origin + (west - origin) % 360
            end = min(start + span, origin + 360)
            intervals = [(start, end)]
            if start + span > origin + 360:
                intervals.append((origin, start + span - 360))
            for left, right in intervals:
                area = box(left, south, right, north)
                for hit in tree.query(area):
                    region = self._regions[self._members[wrapped][hit]]
                    lines = clip_by_rect(
                        tree.geometries[hit].boundary, left, south, right, north
                    )
                    rings = [
                        _display_ring(line, tolerance)
                        for line in get_parts(lines)
                        if line.geom_type in {"LineString", "LinearRing"}
                        and not line.is_empty
                    ]
                    if rings:
                        boundaries.append(
                            {
                                "id": region.id,
                                "level": region.level,
                                "kind": region.airspace_class or region.kind,
                                "rings": rings,
                            }
                        )
        return boundaries

    def artcc_boundaries(self, lat: float, lon: float) -> list[dict]:
        return [
            {
                "id": self._regions[index].id,
                "level": self._regions[index].level,
                "rings": [
                    map_coordinates(ring.coords)
                    for polygon in _polygonal_parts(self._artcc[index])
                    for ring in (polygon.exterior, *polygon.interiors)
                ],
            }
            for index in sorted(self._hits(lat, lon) & self._artcc.keys())
        ]

    def boundaries(self, kind: str) -> list[dict]:
        boundaries = []
        for wrapped, tree in self._trees.items():
            if tree is None:
                continue
            for index, shape in zip(
                self._members[wrapped], tree.geometries, strict=True
            ):
                region = self._regions[index]
                if kind != (
                    region.airspace_class if region.kind == "CLASS" else region.kind
                ):
                    continue
                boundaries.append(
                    {
                        "id": region.id,
                        "level": region.level,
                        "rings": [
                            map_coordinates(ring.coords)
                            for polygon in _polygonal_parts(shape)
                            for ring in (polygon.exterior, *polygon.interiors)
                        ],
                    }
                )
        return boundaries

    def artcc_names(self) -> dict[str, str]:
        return {
            self._regions[index].id: self._regions[index].name for index in self._artcc
        }

    def artcc_extent(
        self, lat: float | None, lon: float | None, *, artcc: str | None = None
    ) -> BaseGeometry:
        if artcc is not None:
            indices = {
                index for index in self._artcc if self._regions[index].id == artcc
            }
        else:
            assert lat is not None and lon is not None
            indices = self._hits(lat, lon) & self._artcc.keys()
        parts = []
        for index in indices:
            shape = self._artcc[index]
            if shape.bounds[2] <= 180:
                parts.append(shape)
            else:
                parts.append(shape.intersection(box(-180, -90, 180, 90)))
                parts.append(
                    translate(shape.intersection(box(180, -90, 360, 90)), xoff=-360)
                )
        return unary_union(parts)


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
