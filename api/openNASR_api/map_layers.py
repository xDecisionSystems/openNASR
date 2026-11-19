"""FAA map layers clipped to the ARTCCs that cover a query point."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Literal

from shapely import STRtree
from shapely.affinity import translate
from shapely.geometry import LineString, Point, box
from shapely.geometry.base import BaseGeometry

from openNASR.arrivals import STAR_KEY
from openNASR.departure import DEPARTURE_KEY
from openNASR.flightplan import RouteResolver
from openNASR.nasr import NASR
from openNASR.plotting import PlottingIndex

from .airspace import map_coordinates
from .lookups import _survey_position, procedure_branches

LayerName = Literal[
    "airports",
    "departures",
    "arrivals",
    "airways",
    "fixes",
    "vors",
    "ndbs",
    "other-navaids",
]
Coordinate = tuple[float, float]
MapFeature = tuple[str, BaseGeometry] | tuple[str, Point, str]
_WEST = box(-180, -90, 180, 90)
_EAST = box(180, -90, 360, 90)


def _lines(shape: BaseGeometry) -> Iterator[LineString]:
    if isinstance(shape, LineString) and not shape.is_empty:
        yield shape
    for child in getattr(shape, "geoms", ()):
        yield from _lines(child)


def _split_leg(start: Coordinate, end: Coordinate) -> Iterator[LineString]:
    if abs(start[0] - end[0]) <= 180:
        yield LineString((start, end))
        return
    line = LineString(((lon % 360, lat) for lon, lat in (start, end)))
    yield from _lines(line.intersection(_WEST))
    yield from _lines(translate(line.intersection(_EAST), xoff=-360))


def _procedure_legs(
    nasr: NASR, layer: LayerName, resolver: RouteResolver
) -> Iterator[tuple[Coordinate, Coordinate]]:
    prefix, keys = (
        ("DP", DEPARTURE_KEY) if layer == "departures" else ("STAR", STAR_KEY)
    )
    frame = nasr.get(f"{prefix}_RTE")
    if frame is None or frame.empty or not set(keys).issubset(frame.columns):
        return

    def sequence(row):
        return int(row["POINT_SEQ"]) if str(row.get("POINT_SEQ", "")).isdecimal() else 0

    for _, group in frame.groupby(list(keys), sort=False, dropna=False):
        rows = group.fillna("").to_dict(orient="records")
        rows.sort(key=sequence)
        for branch in procedure_branches(rows, resolver.procedure_waypoint):
            previous = None
            for waypoint in branch["waypoints"]:
                point = waypoint["position"]
                current = (point["lon"], point["lat"]) if point else None
                if current is not None and previous is not None and current != previous:
                    yield previous, current
                previous = current


def _point_features(nasr: NASR, layer: LayerName) -> Iterator[MapFeature]:
    table = {"airports": "APT_BASE", "fixes": "FIX_BASE"}.get(layer, "NAV_BASE")
    frame = nasr.get(table)
    if frame is None:
        return
    for row in frame.fillna("").to_dict(orient="records"):
        symbol = ""
        if table == "APT_BASE":
            if row.get("SITE_TYPE_CODE") != "A":
                continue
            name = row.get("ICAO_ID") or row.get("ARPT_ID", "")
        elif table == "FIX_BASE":
            name = row.get("FIX_ID", "")
            use = row.get("FIX_USE_CODE", "").strip().upper()
            symbol = {"WP": "WAYPOINT", "MW": "WAYPOINT", "CN": "CNF"}.get(use, "FIX")
            if symbol != "CNF" and row.get("COMPULSORY", "").strip():
                symbol += "-COMPULSORY"
        else:
            nav_type = row.get("NAV_TYPE", "").strip().upper()
            if not nav_type:
                continue
            if nav_type in {"VOR", "VOR/DME", "VORTAC"}:
                group = "vors"
            elif nav_type in {"NDB", "NDB/DME", "MARINE NDB"}:
                group = "ndbs"
            else:
                group = "other-navaids"
            if layer != group:
                continue
            name = row.get("NAV_ID", "")
            symbol = nav_type
        point = _survey_position(row)
        if point:
            geometry = Point(point["lon"], point["lat"])
            yield (name, geometry, symbol) if symbol else (name, geometry)


class MapLayer:
    """Spatial index over one cycle's airport points or published route legs."""

    def __init__(self, features: Iterable[MapFeature]) -> None:
        self._features = list(features)
        self._tree = STRtree([feature[1] for feature in self._features])

    @classmethod
    def from_nasr(
        cls, nasr: NASR, layer: LayerName, resolver: RouteResolver | None
    ) -> MapLayer:
        if layer in {"airports", "fixes", "vors", "ndbs", "other-navaids"}:
            return cls(_point_features(nasr, layer))
        legs: Iterable[tuple[Coordinate, Coordinate]]
        if layer == "airways":
            tables = {
                name: frame
                for name in ("AWY_BASE", "AWY_SEG_ALT", "FIX_BASE", "NAV_BASE")
                if (frame := nasr.get(name)) is not None
            }
            legs = (
                (line.coords[0], line.coords[-1])
                for _, line in PlottingIndex(tables).airway_segments()
            )
        else:
            assert resolver is not None
            legs = _procedure_legs(nasr, layer, resolver)
        seen = set()
        lines: list[tuple[str, BaseGeometry]] = []
        for start, end in legs:
            key = (min(start, end), max(start, end))
            if key not in seen:
                seen.add(key)
                lines.extend(("", geometry) for geometry in _split_leg(start, end))
        return cls(lines)

    def within(self, extent: BaseGeometry) -> dict:
        points = []
        lines: list[list[dict[str, float]]] = []
        for hit in sorted(self._tree.query(extent, predicate="intersects")):
            name, feature, *symbols = self._features[hit]
            if isinstance(feature, Point):
                point = {"name": name, "lat": feature.y, "lon": feature.x}
                if symbols:
                    point["symbol"] = symbols[0]
                points.append(point)
            else:
                lines.extend(
                    map_coordinates(line.coords)
                    for line in _lines(feature.intersection(extent))
                )
        return {"points": points, "lines": lines}
