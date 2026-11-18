"""The JSON shape of a resolved route, shared by the CLI and the HTTP API."""

from __future__ import annotations

from typing import Any

from .geo import densify
from .icaomessage import IcaoFlightPlan
from .routeresult import RouteResult


def route_result_to_dict(
    result: RouteResult,
    extracted: IcaoFlightPlan | None = None,
    max_segment_nm: float | None = None,
) -> dict[str, Any]:
    """Serialize a result exactly as ``POST /v1/route/resolve`` returns it.

    Raises :class:`ValueError` if ``max_segment_nm`` would produce too many points.
    """

    points = list(result.waypoints)
    if max_segment_nm is not None:
        points = densify(points, max_segment_nm)
    coordinates = [[p.lon, p.lat] for p in points]  # GeoJSON is lon, lat
    geometry = (
        {"type": "LineString", "coordinates": coordinates}
        if len(coordinates) >= 2
        else None
    )
    return {
        "input": {
            "mode": "icao_message" if extracted else "route",
            "extracted": {
                "message_type": extracted.message_type,
                "aircraft_id": extracted.aircraft_id,
                "departure": extracted.departure,
                "destination": extracted.destination,
                "route_field": extracted.route_field,
            }
            if extracted
            else None,
        },
        "route": result.route,
        "cycle": result.cycle,
        "complete": result.complete,
        "points": [
            {
                "lat": p.lat,
                "lon": p.lon,
                "name": p.name,
                "kind": p.kind,
                "via": p.via,
                "segment": p.segment,
            }
            for p in points
        ],
        "geojson": {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "route": result.route,
                "cycle": result.cycle,
                "complete": result.complete,
            },
        },
        "diagnostics": [
            {
                "code": d.code,
                "severity": d.severity,
                "message": d.message,
                "token": d.token,
                "position": d.position,
                "detail": d.detail,
            }
            for d in result.diagnostics
        ],
    }
