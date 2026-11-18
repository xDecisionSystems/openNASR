"""Coordinate-projection helpers; distances are measured in nautical miles."""

from .cfcn import calcAngle, ll2xy, radiusOfEarth, xy2ll

__all__ = ["calcAngle", "ll2xy", "radiusOfEarth", "xy2ll"]
