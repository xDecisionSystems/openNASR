import pandas as pd
import pytest

from openNASR.exceptions import RecordNotFoundError
from openNASR.flightplan import flight_plan_path


@pytest.fixture
def tables():
    return {
        "APT_BASE": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "ICAO_ID": "KAAA",
                    "LAT_DECIMAL": "38",
                    "LONG_DECIMAL": "-77",
                },
                {
                    "ARPT_ID": "BBB",
                    "ICAO_ID": "KBBB",
                    "LAT_DECIMAL": "35",
                    "LONG_DECIMAL": "-80",
                },
            ]
        ),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "ALPHA", "LAT_DECIMAL": "37", "LONG_DECIMAL": "-78"},
                {"FIX_ID": "BRAVO", "LAT_DECIMAL": "36", "LONG_DECIMAL": "-79"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(),
        "AWY_BASE": pd.DataFrame(
            [
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                    "AWY_DESIGNATION": "V",
                }
            ]
        ),
        "AWY_SEG_ALT": pd.DataFrame(
            [
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                    "POINT_SEQ": "1",
                    "FROM_POINT": "ALPHA",
                    "TO_POINT": "BRAVO",
                },
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                    "POINT_SEQ": "2",
                    "FROM_POINT": "BRAVO",
                    "TO_POINT": "BBB",
                },
            ]
        ),
    }


def test_flight_plan_path_expands_airways_and_resolves_airports(tables):
    assert flight_plan_path(tables, "KAAA DCT ALPHA V1 BBB") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (36.0, -79.0),
        (35.0, -80.0),
    )


def test_flight_plan_path_expands_an_airway_in_reverse(tables):
    assert flight_plan_path(tables, "BBB V1 ALPHA KAAA") == (
        (35.0, -80.0),
        (36.0, -79.0),
        (37.0, -78.0),
        (38.0, -77.0),
    )


def test_flight_plan_path_rejects_unknown_waypoints(tables):
    with pytest.raises(RecordNotFoundError, match="Flight-plan waypoint"):
        flight_plan_path(tables, "KAAA UNKNOWN")
