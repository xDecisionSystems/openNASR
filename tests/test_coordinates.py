import pytest

import numpy as np

from openNASR.coordinates import ll2xy, xy2ll


def test_projection_uses_latitude_longitude_order():
    east_x, east_y, _, _ = ll2xy(40.0, -74.0, llc=(40.0, -75.0))
    north_x, north_y, _, _ = ll2xy(41.0, -75.0, llc=(40.0, -75.0))

    assert east_x > 0
    assert abs(east_x) > abs(east_y)
    assert north_x == pytest.approx(0.0, abs=1e-10)
    assert north_y > 0


def test_projection_round_trips_within_coordinate_tolerance():
    latitudes = np.array([39.0, 40.5, 41.0])
    longitudes = np.array([-76.0, -74.5, -73.0])
    center = (40.0, -75.0)

    x, y, _, _ = ll2xy(latitudes, longitudes, llc=center)
    actual_latitudes, actual_longitudes = xy2ll(x, y, llc=center)

    assert actual_latitudes == pytest.approx(latitudes, abs=1e-9)
    assert actual_longitudes == pytest.approx(longitudes, abs=1e-9)
