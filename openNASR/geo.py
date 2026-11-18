"""Great-circle geometry for the opt-in densified path."""

from __future__ import annotations

from collections.abc import Sequence
import math

from openNASR.routeresult import RoutePoint

EARTH_RADIUS_NM = 3440.065
MAX_POINTS = 10_000


def distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(min(1.0, math.sqrt(a)))


def intermediate(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> tuple[float, float]:
    """The point ``fraction`` of the way along the great circle."""

    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)
    delta = distance_nm(lat1, lon1, lat2, lon2) / EARTH_RADIUS_NM
    if delta == 0:
        return lat1, lon1
    a = math.sin((1 - fraction) * delta) / math.sin(delta)
    b = math.sin(fraction * delta) / math.sin(delta)
    x = a * math.cos(phi1) * math.cos(lam1) + b * math.cos(phi2) * math.cos(lam2)
    y = a * math.cos(phi1) * math.sin(lam1) + b * math.cos(phi2) * math.sin(lam2)
    z = a * math.sin(phi1) + b * math.sin(phi2)
    return (
        math.degrees(math.atan2(z, math.hypot(x, y))),
        math.degrees(math.atan2(y, x)),
    )


def densify(points: Sequence[RoutePoint], max_segment_nm: float) -> list[RoutePoint]:
    """Insert great-circle points so no leg is longer than ``max_segment_nm``.

    Inserted points have kind ``interpolated`` and no name. Raises
    :class:`ValueError` rather than return more than :data:`MAX_POINTS`.
    """

    result: list[RoutePoint] = []
    for before, after in zip(points, points[1:]):
        result.append(before)
        legs = math.ceil(
            distance_nm(before.lat, before.lon, after.lat, after.lon) / max_segment_nm
        )
        for step in range(1, legs):
            lat, lon = intermediate(
                before.lat, before.lon, after.lat, after.lon, step / legs
            )
            result.append(RoutePoint(lat, lon, "", "interpolated", None, after.segment))
        if len(result) > MAX_POINTS:
            raise ValueError(
                f"max_segment_nm={max_segment_nm} would produce more than "
                f"{MAX_POINTS} points"
            )
    if points:
        result.append(points[-1])
    return result
