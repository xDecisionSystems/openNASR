"""Which controlled regions contain a point, from the FAA boundary tables.

Only ``ARB_BASE``/``ARB_SEG`` carry polygons: ARTCC low and high boundaries and
the FIR, CTA and UTA regions beyond them. The FAA CSV data holds no Class
B/C/D/E polygons (``CLS_ARSP`` only says which class an airport has), so those
cannot be answered here. Arcs are approximated by their published vertices.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

from pandas import DataFrame
from shapely import STRtree, unary_union
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

LOGGER = logging.getLogger("openNASR_api")

NOT_COVERED = (
    "Class B/C/D/E airspace, special-use airspace and MOAs are not in the FAA "
    "CSV data as polygons; only ARTCC, FIR, CTA and UTA boundaries are searched."
)


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    kind: str  # ARTCC | FIR | CTA | UTA | CTA/FIR
    level: str  # low | high | unlimited


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


class AirspaceIndex:
    """A spatial index over one cycle's ARTCC/FIR/CTA/UTA boundaries."""

    def __init__(self, base: DataFrame, segments: DataFrame) -> None:
        names = {
            str(row["LOCATION_ID"]).strip().upper(): str(row.get("LOCATION_NAME", ""))
            for row in base.to_dict(orient="records")
        }
        self._regions: list[Region] = []
        self._wraps: list[bool] = []
        shapes = []
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
            shapes.append(shape)
            self._wraps.append(wraps)
        if skipped:
            LOGGER.info("airspace index skipped %d unusable boundaries", skipped)
        self._plain = [i for i, wraps in enumerate(self._wraps) if not wraps]
        self._wrapped = [i for i, wraps in enumerate(self._wraps) if wraps]
        self._trees = {
            False: STRtree([shapes[i] for i in self._plain]) if self._plain else None,
            True: STRtree([shapes[i] for i in self._wrapped])
            if self._wrapped
            else None,
        }

    def __len__(self) -> int:
        return len(self._regions)

    def at(self, lat: float, lon: float) -> list[Region]:
        found: list[Region] = []
        for wrapped, members in ((False, self._plain), (True, self._wrapped)):
            tree = self._trees[wrapped]
            if tree is None:
                continue
            x = lon + 360 if wrapped and lon < 0 else lon
            for hit in tree.query(Point(x, lat), predicate="intersects"):
                found.append(self._regions[members[hit]])
        return sorted(found, key=lambda r: (r.id, r.level, r.kind))
