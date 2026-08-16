import pytest

import numpy as np

from openNASR.coordinates import ll2xy, xy2ll
from openNASR.airport import makeRWYpoly


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

    assert isinstance(x, np.ndarray)
    assert isinstance(y, np.ndarray)
    assert actual_latitudes == pytest.approx(latitudes, abs=1e-9)
    assert actual_longitudes == pytest.approx(longitudes, abs=1e-9)


def test_inverse_projection_handles_projection_center_without_warnings():
    with np.errstate(divide="raise", invalid="raise"):
        latitude, longitude = xy2ll(0.0, 0.0, llc=(40.0, -75.0))

    assert latitude == pytest.approx(40.0)
    assert longitude == pytest.approx(-75.0)


def test_projection_accepts_scalar_inputs():
    x, y, _, distance = ll2xy(40.0, -75.0, llc=(40.0, -75.0))

    assert np.ndim(x) == np.ndim(y) == np.ndim(distance) == 0


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)],
)
def test_projection_rejects_invalid_geographic_coordinates(latitude, longitude):
    with pytest.raises(ValueError):
        ll2xy(latitude, longitude, llc=(0.0, 0.0))


def test_inverse_projection_rejects_an_invalid_center():
    with pytest.raises(ValueError, match="latitude"):
        xy2ll(0.0, 0.0, llc=(100.0, 0.0))


def test_runway_width_is_converted_from_feet_to_nautical_miles():
    polygon = makeRWYpoly((0.0, 0.0), (1.0, 0.0), width=6076.1)

    assert polygon.bounds[1] == pytest.approx(-0.5)
    assert polygon.bounds[3] == pytest.approx(0.5)
