import pandas as pd
import pytest

from openNASR.exceptions import AmbiguousRecordError, RecordNotFoundError
from openNASR.flightplan import (
    _RouteToken,
    _WaypointResolver,
    _tokenize_flight_plan,
    flight_plan_path,
)


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


def test_flight_plan_path_prefers_faa_and_icao_airports_at_endpoints(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "AAA", "LAT_DECIMAL": "1", "LONG_DECIMAL": "2"},
                    {"FIX_ID": "KBBB", "LAT_DECIMAL": "3", "LONG_DECIMAL": "4"},
                ]
            ),
        ],
        ignore_index=True,
    )

    assert flight_plan_path(tables, "AAA ALPHA KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),
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
        [{"DP_NAME": "ALPHA", "ARTCC": "ZJX", "DP_COMPUTER_CODE": "ALPHA1"}]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "ALPHA",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "ALPHA1",
                "ROUTE_PORTION_TYPE": "TRANSITION",
                "TRANSITION_COMPUTER_CODE": "ALPHA1.ALPHA",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "ALPHA",
            },
            {
                "DP_NAME": "ALPHA",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "ALPHA1",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
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


def test_flight_plan_path_resolves_bare_star_before_airway_lookup(tables):
    """A bare STAR name that looks like an airway retains its route connection."""

    tables["APT_BASE"] = pd.concat(
        [
            tables["APT_BASE"],
            pd.DataFrame(
                [
                    {
                        "ARPT_ID": "ATL",
                        "ICAO_ID": "KATL",
                        "LAT_DECIMAL": "33.64",
                        "LONG_DECIMAL": "-84.43",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "GOLLM", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-83"},
                    {"FIX_ID": "LANCE", "LAT_DECIMAL": "33.8", "LONG_DECIMAL": "-84"},
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["STAR_BASE"] = pd.DataFrame(
        [{"STAR_COMPUTER_CODE": "GNDLF3", "ARTCC": "ZTL"}]
    )
    # STAR records are stored from the terminal outward, so GOLLM is the
    # procedure connection and KATL is its intended exit in the filed order.
    tables["STAR_RTE"] = pd.DataFrame(
        [
            {
                "STAR_COMPUTER_CODE": "GNDLF3",
                "ARTCC": "ZTL",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "KATL",
            },
            {
                "STAR_COMPUTER_CODE": "GNDLF3",
                "ARTCC": "ZTL",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "LANCE",
            },
            {
                "STAR_COMPUTER_CODE": "GNDLF3",
                "ARTCC": "ZTL",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "30",
                "POINT": "GOLLM",
            },
        ]
    )

    assert flight_plan_path(tables, "KAAA GOLLM GNDLF3 KATL/0043") == (
        (38.0, -77.0),
        (34.0, -83.0),  # Procedure connection point.
        (33.8, -84.0),
        (33.64, -84.43),  # Procedure exit and following destination token.
    )


def test_flight_plan_path_resolves_bare_departure_after_origin(tables):
    tables["DP_BASE"] = pd.DataFrame(
        [{"DP_NAME": "RUGGD", "ARTCC": "ZJX", "DP_COMPUTER_CODE": "RUGGD3"}]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "RUGGD",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "RUGGD3",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "KAAA",
            },
            {
                "DP_NAME": "RUGGD",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "RUGGD3",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "ALPHA",
            },
            {
                "DP_NAME": "RUGGD",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "RUGGD3",
                "BODY_SEQ": "1",
                "POINT_SEQ": "30",
                "POINT": "BRAVO",
            },
        ]
    )

    assert flight_plan_path(tables, "KAAA RUGGD3 BRAVO KBBB") == (
        (38.0, -77.0),  # Origin and departure procedure connection.
        (37.0, -78.0),
        (36.0, -79.0),  # Departure exit and following route token.
        (35.0, -80.0),
    )


def test_flight_plan_path_resolves_bare_arrival_before_destination(tables):
    tables["STAR_BASE"] = pd.DataFrame(
        [{"STAR_COMPUTER_CODE": "SCAMR4", "ARTCC": "ZJX"}]
    )
    tables["STAR_RTE"] = pd.DataFrame(
        [
            {
                "STAR_COMPUTER_CODE": "SCAMR4",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "KBBB",
            },
            {
                "STAR_COMPUTER_CODE": "SCAMR4",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "BRAVO",
            },
            {
                "STAR_COMPUTER_CODE": "SCAMR4",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "30",
                "POINT": "ALPHA",
            },
        ]
    )

    assert flight_plan_path(tables, "KAAA ALPHA SCAMR4 KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),  # Arrival procedure connection.
        (36.0, -79.0),
        (35.0, -80.0),  # Arrival exit and following destination token.
    )


def test_dotted_pair_does_not_hide_filed_fix_before_airway(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "HAYGR", "LAT_DECIMAL": "37", "LONG_DECIMAL": "-78"},
                    {"FIX_ID": "MCRAY", "LAT_DECIMAL": "36", "LONG_DECIMAL": "-79"},
                    {"FIX_ID": "MID", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-80"},
                    {"FIX_ID": "LEJOY", "LAT_DECIMAL": "33", "LONG_DECIMAL": "-81"},
                    {"FIX_ID": "BAD", "LAT_DECIMAL": "32", "LONG_DECIMAL": "-82"},
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["DP_BASE"] = pd.DataFrame(
        [
            {"DP_NAME": "MCRAY", "ARTCC": "ZDC", "DP_COMPUTER_CODE": "MCRAY2"},
            {
                "DP_NAME": "MCRAY",
                "ARTCC": "ZDC",
                "DP_COMPUTER_CODE": "MCRAY2.MCRAY",
            },
        ]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "MCRAY",
                "ARTCC": "ZDC",
                "DP_COMPUTER_CODE": code,
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "KAAA",
            }
            for code in ("MCRAY2", "MCRAY2.MCRAY")
        ]
        + [
            {
                "DP_NAME": "MCRAY",
                "ARTCC": "ZDC",
                "DP_COMPUTER_CODE": code,
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "HAYGR",
            }
            for code in ("MCRAY2", "MCRAY2.MCRAY")
        ]
    )
    tables["AWY_BASE"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "A",
                "AWY_ID": "178",
                "AWY_DESIGNATION": "Q",
            },
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "B",
                "AWY_ID": "178",
                "AWY_DESIGNATION": "Q",
            },
        ]
    )
    tables["AWY_SEG_ALT"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "A",
                "AWY_ID": "178",
                "POINT_SEQ": "1",
                "FROM_POINT": "HAYGR",
                "TO_POINT": "BAD",
            },
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "A",
                "AWY_ID": "178",
                "POINT_SEQ": "2",
                "FROM_POINT": "BAD",
                "TO_POINT": "LEJOY",
            },
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "B",
                "AWY_ID": "178",
                "POINT_SEQ": "3",
                "FROM_POINT": "MCRAY",
                "TO_POINT": "MID",
            },
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "B",
                "AWY_ID": "178",
                "POINT_SEQ": "4",
                "FROM_POINT": "MID",
                "TO_POINT": "LEJOY",
            },
        ]
    )

    assert flight_plan_path(tables, "KAAA.MCRAY2.MCRAY.Q178.LEJOY.KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),  # Bare DP exit.
        (36.0, -79.0),  # Filed MCRAY fix, the Q178 connection.
        (34.0, -80.0),  # Q178 starts from MCRAY, not HAYGR.
        (33.0, -81.0),
        (35.0, -80.0),
    )


def test_star_body_uses_preceding_route_token_and_preserves_ambiguity(tables):
    tables["STAR_BASE"] = pd.DataFrame(
        [{"STAR_COMPUTER_CODE": "CHOICE3", "ARTCC": "ZJX"}]
    )
    tables["STAR_RTE"] = pd.DataFrame(
        [
            {
                "STAR_COMPUTER_CODE": "CHOICE3",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "ROUTE_NAME": route_name,
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": point_sequence,
                "POINT": point,
            }
            for route_name, entry in (
                ("ALPHA ARRIVAL", "ALPHA"),
                ("BRAVO ARRIVAL", "BRAVO"),
            )
            for point_sequence, point in (("10", "KBBB"), ("20", entry))
        ]
    )

    assert flight_plan_path(tables, "KAAA ALPHA CHOICE3 KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),  # Filed STAR connection selects ALPHA ARRIVAL.
        (35.0, -80.0),
    )
    with pytest.raises(AmbiguousRecordError, match="StarProcedure"):
        flight_plan_path(tables, "KAAA CHOICE3 KBBB")


def test_flight_plan_path_combines_procedures_direct_airway_and_navaid(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "ENTRY", "LAT_DECIMAL": "33", "LONG_DECIMAL": "-80"},
                    {
                        "FIX_ID": "STARFIX",
                        "LAT_DECIMAL": "32",
                        "LONG_DECIMAL": "-81",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["NAV_BASE"] = pd.DataFrame(
        [{"NAV_ID": "NAV", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-79"}]
    )
    tables["DP_BASE"] = pd.DataFrame(
        [{"DP_NAME": "DEP", "ARTCC": "ZJX", "DP_COMPUTER_CODE": "DEP1"}]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "DEP",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "DEP1",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "KAAA",
            },
            {
                "DP_NAME": "DEP",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "DEP1",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "ALPHA",
            },
        ]
    )
    tables["STAR_BASE"] = pd.DataFrame(
        [{"STAR_COMPUTER_CODE": "ARR1", "ARTCC": "ZJX"}]
    )
    tables["STAR_RTE"] = pd.DataFrame(
        [
            {
                "STAR_COMPUTER_CODE": "ARR1",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "KBBB",
            },
            {
                "STAR_COMPUTER_CODE": "ARR1",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "STARFIX",
            },
            {
                "STAR_COMPUTER_CODE": "ARR1",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": "30",
                "POINT": "ENTRY",
            },
        ]
    )
    tables["AWY_BASE"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "D",
                "AWY_ID": "1",
                "AWY_DESIGNATION": "V",
            }
        ]
    )
    tables["AWY_SEG_ALT"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "D",
                "AWY_ID": "1",
                "POINT_SEQ": "1",
                "FROM_POINT": "ALPHA",
                "TO_POINT": "NAV",
            }
        ]
    )

    assert flight_plan_path(
        tables, "KAAA.DEP1..ALPHA.V1.NAV..ENTRY.ARR1.KBBB"
    ) == (
        (38.0, -77.0),  # Origin and DP join.
        (37.0, -78.0),  # DP exit and airway entry.
        (34.0, -79.0),  # Airway navaid.
        (33.0, -80.0),  # Direct segment's filed STAR connection.
        (32.0, -81.0),
        (35.0, -80.0),  # STAR exit and destination join.
    )


def test_flight_plan_path_accepts_double_dot_direct_routing(tables):
    assert flight_plan_path(tables, "KAAA..ALPHA..BBB/0354") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (35.0, -80.0),
    )


def test_tokenizer_retains_source_positions_when_stripping_speed_altitude(tables):
    resolver = _WaypointResolver(tables)

    assert _tokenize_flight_plan(
        tables, "KAAA ALPHA/0354 BBB", resolver=resolver
    ) == (
        _RouteToken("KAAA", 0),
        _RouteToken("ALPHA", 5),
        _RouteToken("BBB", 16),
    )


def _procedure_matrix_tables():
    """Tiny current-cycle-shaped tables shared by the T2.7 route matrix."""

    points = {
        "KAAA": (38, -77),
        "DEP": (37, -78),
        "TRANS": (36, -79),
        "MID": (35, -80),
        "ARR": (34, -81),
        "KBBB": (33, -82),
    }
    tables = {
        "APT_BASE": pd.DataFrame(
            [
                {"ARPT_ID": name, "ICAO_ID": name, "LAT_DECIMAL": lat, "LONG_DECIMAL": lon}
                for name, (lat, lon) in points.items()
                if name in {"KAAA", "KBBB"}
            ]
        ),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": name, "LAT_DECIMAL": lat, "LONG_DECIMAL": lon}
                for name, (lat, lon) in points.items()
                if name not in {"KAAA", "KBBB"}
            ]
        ),
        "NAV_BASE": pd.DataFrame(),
        "DP_BASE": pd.DataFrame(
            [{"DP_NAME": "DEP", "ARTCC": "ZXX", "DP_COMPUTER_CODE": "DEP1"}]
        ),
        "DP_RTE": pd.DataFrame(
            [
                {
                    "DP_NAME": "DEP",
                    "ARTCC": "ZXX",
                    "DP_COMPUTER_CODE": code,
                    "ROUTE_PORTION_TYPE": portion,
                    "TRANSITION_COMPUTER_CODE": transition,
                    "BODY_SEQ": "1",
                    "POINT_SEQ": str(sequence),
                    "POINT": point,
                }
                for code, portion, transition, sequence, point in (
                    ("DEP1", "BODY", "", 10, "TRANS"),
                    ("DEP1", "BODY", "", 20, "DEP"),
                    ("DEP1", "TRANSITION", "DEP1.TRANS", 10, "KAAA"),
                    ("DEP1", "TRANSITION", "DEP1.TRANS", 20, "TRANS"),
                )
            ]
        ),
        "STAR_BASE": pd.DataFrame(
            [{"STAR_COMPUTER_CODE": "ARR1", "ARTCC": "ZXX"}]
        ),
        "STAR_RTE": pd.DataFrame(
            [
                {
                    "STAR_COMPUTER_CODE": "ARR1",
                    "ARTCC": "ZXX",
                    "ROUTE_PORTION_TYPE": portion,
                    "TRANSITION_COMPUTER_CODE": transition,
                    "BODY_SEQ": "1",
                    "POINT_SEQ": str(sequence),
                    "POINT": point,
                }
                for portion, transition, sequence, point in (
                    ("BODY", "", 10, "KBBB"),
                    ("BODY", "", 20, "MID"),
                    ("TRANSITION", "TRANS.ARR1", 10, "MID"),
                    ("TRANSITION", "TRANS.ARR1", 20, "ARR"),
                )
            ]
        ),
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
                    "FROM_POINT": "DEP",
                    "TO_POINT": "MID",
                }
            ]
        ),
    }
    return tables


@pytest.mark.parametrize(
    ("name", "route", "expected"),
    (
        (
            "bare DP",
            "KAAA DEP1 KBBB",
            ((38.0, -77.0), (36.0, -79.0), (37.0, -78.0), (33.0, -82.0)),
        ),
        (
            "dotted DP",
            "KAAA.DEP1.TRANS KBBB",
            ((38.0, -77.0), (36.0, -79.0), (37.0, -78.0), (33.0, -82.0)),
        ),
        (
            "bare STAR",
            "KAAA ARR1 KBBB",
            ((38.0, -77.0), (35.0, -80.0), (33.0, -82.0)),
        ),
        (
            "dotted STAR",
            "KAAA TRANS.ARR1 KBBB",
            ((38.0, -77.0), (34.0, -81.0), (35.0, -80.0), (33.0, -82.0)),
        ),
        (
            "DP-to-airway",
            "KAAA DEP1 V1 MID KBBB",
            ((38.0, -77.0), (36.0, -79.0), (37.0, -78.0), (35.0, -80.0), (33.0, -82.0)),
        ),
        (
            "airway-to-STAR",
            "KAAA DEP V1 MID ARR1 KBBB",
            ((38.0, -77.0), (37.0, -78.0), (35.0, -80.0), (33.0, -82.0)),
        ),
        (
            "procedure-only airport pair",
            "KAAA DEP1 ARR1 KBBB",
            ((38.0, -77.0), (36.0, -79.0), (37.0, -78.0), (35.0, -80.0), (33.0, -82.0)),
        ),
    ),
)
def test_current_cycle_procedure_matrix(name, route, expected):
    """T2.7 matrix; synthetic rows model the pinned 2026-05-14 cycle."""

    assert name
    assert flight_plan_path(_procedure_matrix_tables(), route) == expected
