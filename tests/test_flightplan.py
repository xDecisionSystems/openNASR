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


def test_flight_plan_path_uses_route_position_to_disambiguate_waypoints(tables):
    tables["APT_BASE"] = pd.concat(
        [
            tables["APT_BASE"],
            pd.DataFrame(
                [
                    {
                        "ARPT_ID": "TRM",
                        "ICAO_ID": "KTRM",
                        "LAT_DECIMAL": "33",
                        "LONG_DECIMAL": "-116",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["NAV_BASE"] = pd.DataFrame(
        [{"NAV_ID": "TRM", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-117"}]
    )

    assert flight_plan_path(tables, "AAA TRM BBB") == (
        (38.0, -77.0),
        (34.0, -117.0),
        (35.0, -80.0),
    )


def test_flight_plan_path_expands_departure_and_arrival_procedures(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "ENTRY", "LAT_DECIMAL": "40", "LONG_DECIMAL": "-81"},
                    {"FIX_ID": "MERGE", "LAT_DECIMAL": "41", "LONG_DECIMAL": "-82"},
                    {"FIX_ID": "DEST", "LAT_DECIMAL": "42", "LONG_DECIMAL": "-83"},
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["DP_BASE"] = pd.DataFrame(
        [{"DP_NAME": "ALPHA", "ARTCC": "ZJX", "DP_COMPUTER_CODE": "ALPHA1.ALPHA"}]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "ALPHA",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "ALPHA1.ALPHA",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "ALPHA",
            },
            {
                "DP_NAME": "ALPHA",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "ALPHA1.ALPHA",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "BRAVO",
            },
        ]
    )
    tables["STAR_BASE"] = pd.DataFrame(
        [{"STAR_COMPUTER_CODE": "MERGE.STAR1", "ARTCC": "ZJX"}]
    )
    tables["STAR_RTE"] = pd.DataFrame(
        [
            {
                "STAR_COMPUTER_CODE": "MERGE.STAR1",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "DEST",
            },
            {
                "STAR_COMPUTER_CODE": "MERGE.STAR1",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "MERGE",
            },
            {
                "STAR_COMPUTER_CODE": "MERGE.STAR1",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "TRANSITION",
                "TRANSITION_COMPUTER_CODE": "ENTRY.STAR1",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "MERGE",
            },
            {
                "STAR_COMPUTER_CODE": "MERGE.STAR1",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "TRANSITION",
                "TRANSITION_COMPUTER_CODE": "ENTRY.STAR1",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "ENTRY",
            },
        ]
    )
    tables["AWY_BASE"] = pd.concat(
        [
            tables["AWY_BASE"],
            pd.DataFrame(
                [
                    {
                        "REGULATORY": "Y",
                        "AWY_LOCATION": "D",
                        "AWY_ID": "J1",
                        "AWY_DESIGNATION": "J",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["AWY_SEG_ALT"] = pd.concat(
        [
            tables["AWY_SEG_ALT"],
            pd.DataFrame(
                [
                    {
                        "REGULATORY": "Y",
                        "AWY_LOCATION": "D",
                        "AWY_ID": "J1",
                        "POINT_SEQ": "1",
                        "FROM_POINT": "BRAVO",
                        "TO_POINT": "ENTRY",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    assert flight_plan_path(tables, "ALPHA1.ALPHA.J1.ENTRY.STAR1/0354") == (
        (37.0, -78.0),
        (36.0, -79.0),
        (40.0, -81.0),
        (41.0, -82.0),
        (42.0, -83.0),
    )


def test_flight_plan_path_accepts_double_dot_direct_routing(tables):
    assert flight_plan_path(tables, "KAAA..ALPHA..BBB/0354") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (35.0, -80.0),
    )
