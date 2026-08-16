import pytest

from openNASR.coordinates import ll2xy


def test_projection_uses_latitude_longitude_order():
    east_x, east_y, _, _ = ll2xy(40.0, -74.0, llc=(40.0, -75.0))
    north_x, north_y, _, _ = ll2xy(41.0, -75.0, llc=(40.0, -75.0))

    assert east_x > 0
    assert abs(east_x) > abs(east_y)
    assert north_x == pytest.approx(0.0, abs=1e-10)
    assert north_y > 0
