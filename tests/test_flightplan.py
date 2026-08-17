import pandas as pd
import pytest

from openNASR import (
    RouteResolver as PublicRouteResolver,
    UnsupportedRouteContentError as PublicUnsupportedRouteContentError,
)
from openNASR.exceptions import (
    AmbiguousRecordError,
    RecordNotFoundError,
    RouteConnectivityError,
    UnsupportedRouteContentError,
)
from openNASR.flightplan import (
    RouteResolver,
    _ProcedureIndex,
    _RouteToken,
    _WaypointResolver,
    _is_published_dotted_procedure,
    _procedure_path,
    _text,
    _tokenize_flight_plan,
    flight_plan_path,
)


def test_procedure_index_matches_direct_normalized_filters():
    tables = {
        "DP_BASE": pd.DataFrame(
            [
                {"DP_COMPUTER_CODE": "ALPHA1", "ROW": "first"},
                {"DP_COMPUTER_CODE": "BRAVO2", "ROW": "other"},
                {"DP_COMPUTER_CODE": " alpha1 ", "ROW": "last"},
            ]
        ),
        "DP_RTE": pd.DataFrame(
            [
                {"TRANSITION_COMPUTER_CODE": "DPTRANS", "ROW": "first"},
                {"TRANSITION_COMPUTER_CODE": "OTHER", "ROW": "other"},
                {"TRANSITION_COMPUTER_CODE": " dptrans ", "ROW": "last"},
            ]
        ),
        "STAR_BASE": pd.DataFrame(
            [
                {"STAR_COMPUTER_CODE": "STAR1", "ROW": "first"},
                {"STAR_COMPUTER_CODE": "OTHER", "ROW": "other"},
                {"STAR_COMPUTER_CODE": " star1 ", "ROW": "last"},
            ]
        ),
        "STAR_RTE": pd.DataFrame(
            [
                {"TRANSITION_COMPUTER_CODE": "STARTRANS", "ROW": "first"},
                {"TRANSITION_COMPUTER_CODE": "OTHER", "ROW": "other"},
                {"TRANSITION_COMPUTER_CODE": " startrans ", "ROW": "last"},
            ]
        ),
    }
    index = _ProcedureIndex(tables)

    checks = (
        (index.departure_base(" alpha1 "), "DP_BASE", "DP_COMPUTER_CODE", "ALPHA1"),
        (
            index.departure_transition("dptrans"),
            "DP_RTE",
            "TRANSITION_COMPUTER_CODE",
            "DPTRANS",
        ),
        (index.star_base("STAR1"), "STAR_BASE", "STAR_COMPUTER_CODE", "STAR1"),
        (
            index.star_transition("startrans"),
            "STAR_RTE",
            "TRANSITION_COMPUTER_CODE",
            "STARTRANS",
        ),
    )
    for actual, table, column, token in checks:
        assert actual is not None
        direct = tables[table][tables[table][column].map(_text).eq(token)]
        pd.testing.assert_frame_equal(actual, direct)

    assert index._departure_codes["ALPHA1"].tolist() == [0, 2]
    assert index.departure_base("MISSING").empty


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


def test_route_resolver_reuses_one_waypoint_index(tables, monkeypatch):
    calls = 0
    original_init = _WaypointResolver.__init__

    def tracked_init(self, route_tables):
        nonlocal calls
        calls += 1
        original_init(self, route_tables)

    monkeypatch.setattr(_WaypointResolver, "__init__", tracked_init)

    assert PublicRouteResolver is RouteResolver
    resolver = PublicRouteResolver(tables)
    expected = ((38.0, -77.0), (37.0, -78.0), (35.0, -80.0))

    assert resolver.path("KAAA ALPHA KBBB") == expected
    assert resolver.path("KAAA ALPHA KBBB") == expected
    assert calls == 1
    assert flight_plan_path(tables, "KAAA ALPHA KBBB") == expected
    assert calls == 2


def test_route_resolver_uses_waypoint_snapshot(tables):
    resolver = RouteResolver(tables)
    original = resolver.path("KAAA ALPHA KBBB")
    tables["FIX_BASE"].loc[0, "LAT_DECIMAL"] = "10"

    assert resolver.path("KAAA ALPHA KBBB") == original
    assert RouteResolver(tables).path("KAAA ALPHA KBBB") == (
        (38.0, -77.0),
        (10.0, -78.0),
        (35.0, -80.0),
    )
    assert flight_plan_path(tables, "KAAA ALPHA KBBB") == (
        (38.0, -77.0),
        (10.0, -78.0),
        (35.0, -80.0),
    )


def test_route_resolver_matches_wrapper_lookup_error(tables):
    resolver = RouteResolver(tables)

    with pytest.raises(RecordNotFoundError) as session_error:
        resolver.path("KAAA UNKNOWN")
    with pytest.raises(RecordNotFoundError) as wrapper_error:
        flight_plan_path(tables, "KAAA UNKNOWN")

    assert str(session_error.value) == str(wrapper_error.value)


def test_flight_plan_path_expands_an_airway_in_reverse(tables):
    assert flight_plan_path(tables, "BBB V1 ALPHA KAAA") == (
        (35.0, -80.0),
        (36.0, -79.0),
        (37.0, -78.0),
        (38.0, -77.0),
    )


def test_flight_plan_path_expands_prefixed_airway_ids(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "QSTART", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-81"},
                    {"FIX_ID": "QEND", "LAT_DECIMAL": "33", "LONG_DECIMAL": "-82"},
                    {"FIX_ID": "TSTART", "LAT_DECIMAL": "32", "LONG_DECIMAL": "-83"},
                    {"FIX_ID": "TEND", "LAT_DECIMAL": "31", "LONG_DECIMAL": "-84"},
                    {"FIX_ID": "YSTART", "LAT_DECIMAL": "30", "LONG_DECIMAL": "-85"},
                    {"FIX_ID": "YEND", "LAT_DECIMAL": "29", "LONG_DECIMAL": "-86"},
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["AWY_BASE"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": location,
                "AWY_ID": airway,
                "AWY_DESIGNATION": designation,
            }
            for location, airway, designation in (
                ("Q", "Q1", "RN"),
                ("T", "T2", "AT"),
                ("Y", "Y3", "A"),
            )
        ]
    )
    tables["AWY_SEG_ALT"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": location,
                "AWY_ID": airway,
                "POINT_SEQ": "1",
                "FROM_POINT": start,
                "TO_POINT": end,
            }
            for location, airway, start, end in (
                ("Q", "Q1", "QSTART", "QEND"),
                ("T", "T2", "TSTART", "TEND"),
                ("Y", "Y3", "YSTART", "YEND"),
            )
        ]
    )

    assert flight_plan_path(tables, "KAAA QSTART Q1 QEND KBBB") == (
        (38.0, -77.0),
        (34.0, -81.0),
        (33.0, -82.0),
        (35.0, -80.0),
    )
    assert flight_plan_path(tables, "KAAA TSTART T2 TEND KBBB") == (
        (38.0, -77.0),
        (32.0, -83.0),
        (31.0, -84.0),
        (35.0, -80.0),
    )
    assert flight_plan_path(tables, "KAAA YSTART Y3 YEND KBBB") == (
        (38.0, -77.0),
        (30.0, -85.0),
        (29.0, -86.0),
        (35.0, -80.0),
    )


def test_airway_lookup_uses_column_matching_for_base_records(tables, monkeypatch):
    def fail_record_materialization(*args, **kwargs):
        raise AssertionError("airway base must not materialize DataFrame records")

    monkeypatch.setattr(tables["AWY_BASE"], "to_dict", fail_record_materialization)

    assert flight_plan_path(tables, "KAAA ALPHA V1 BBB") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (36.0, -79.0),
        (35.0, -80.0),
    )


def test_flight_plan_path_joins_repeated_airway_tokens(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "QSTART", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-81"},
                    {"FIX_ID": "QMID", "LAT_DECIMAL": "33", "LONG_DECIMAL": "-82"},
                    {"FIX_ID": "QEND", "LAT_DECIMAL": "32", "LONG_DECIMAL": "-83"},
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["AWY_BASE"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "Q",
                "AWY_ID": "Q1",
                "AWY_DESIGNATION": "RN",
            }
        ]
    )
    tables["AWY_SEG_ALT"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "Q",
                "AWY_ID": "Q1",
                "POINT_SEQ": "1",
                "FROM_POINT": "QSTART",
                "TO_POINT": "QMID",
            },
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "Q",
                "AWY_ID": "Q1",
                "POINT_SEQ": "2",
                "FROM_POINT": "QMID",
                "TO_POINT": "QEND",
            },
        ]
    )

    assert flight_plan_path(tables, "KAAA QSTART Q1 QMID Q1 QEND KBBB") == (
        (38.0, -77.0),
        (34.0, -81.0),
        (33.0, -82.0),
        (32.0, -83.0),
        (35.0, -80.0),
    )


def test_flight_plan_path_reports_genuine_airway_ambiguity(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "START", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-81"},
                    {"FIX_ID": "MID_A", "LAT_DECIMAL": "33", "LONG_DECIMAL": "-82"},
                    {"FIX_ID": "MID_B", "LAT_DECIMAL": "32", "LONG_DECIMAL": "-83"},
                    {"FIX_ID": "END", "LAT_DECIMAL": "31", "LONG_DECIMAL": "-84"},
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["AWY_BASE"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "A",
                "AWY_ID": "Q1",
                "AWY_DESIGNATION": "RN",
            },
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "B",
                "AWY_ID": "Q1",
                "AWY_DESIGNATION": "RN",
            },
        ]
    )
    tables["AWY_SEG_ALT"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": location,
                "AWY_ID": "Q1",
                "POINT_SEQ": "1",
                "FROM_POINT": "START",
                "TO_POINT": middle,
            }
            for location, middle in (("A", "MID_A"), ("B", "MID_B"))
        ]
        + [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": location,
                "AWY_ID": "Q1",
                "POINT_SEQ": "2",
                "FROM_POINT": middle,
                "TO_POINT": "END",
            }
            for location, middle in (("A", "MID_A"), ("B", "MID_B"))
        ]
    )

    with pytest.raises(AmbiguousRecordError, match="Airway path"):
        flight_plan_path(tables, "KAAA START Q1 END KBBB")


def test_flight_plan_path_rejects_unknown_waypoints(tables):
    with pytest.raises(RecordNotFoundError, match="Flight-plan waypoint"):
        flight_plan_path(tables, "KAAA UNKNOWN")


def test_flight_plan_errors_include_compact_route_diagnostics(tables):
    route = "KAAA UNKNOWN KBBB"

    with pytest.raises(RecordNotFoundError) as caught:
        RouteResolver(tables).path(route)

    error = caught.value
    assert error.token == "UNKNOWN"
    assert error.position == 5
    assert error.cycle is None
    assert error.route == route
    assert error.route_text == route
    assert error.failure_type == "RecordNotFoundError"


@pytest.mark.parametrize(
    ("token", "content_type"),
    [
        ("EGLL", "foreign_airport"),
        ("UL207", "external_route"),
        ("4500N/05000W", "oceanic_coordinate"),
        ("GFS138045", "radial_distance"),
    ],
)
def test_flight_plan_rejects_recognized_unsupported_route_content(
    tables, token, content_type
):
    route = f"KAAA {token} KBBB"

    with pytest.raises(UnsupportedRouteContentError) as caught:
        RouteResolver(tables).path(route)

    error = caught.value
    assert error.token == token
    assert error.position == 5
    assert error.content_type == content_type
    assert error.cycle is None
    assert error.route == route
    assert error.failure_type == "UnsupportedRouteContentError"


def test_unsupported_route_content_retains_selected_cycle(tables):
    class CycleTables(dict):
        effective_date = "2026-08-13"

    route = "KAAA EGLL KBBB"
    with pytest.raises(PublicUnsupportedRouteContentError) as caught:
        RouteResolver(CycleTables(tables)).path(route)

    error = caught.value
    assert error.cycle == "2026-08-13"
    assert error.token == "EGLL"
    assert error.position == 5
    assert error.route_text == route


def test_alphanumeric_waypoints_do_not_use_airway_dispatch(tables):
    tables["APT_BASE"] = pd.concat(
        [
            tables["APT_BASE"],
            pd.DataFrame(
                [
                    {
                        "ARPT_ID": "E91",
                        "ICAO_ID": "KE91",
                        "LAT_DECIMAL": "40",
                        "LONG_DECIMAL": "-75",
                    },
                    {
                        "ARPT_ID": "O60",
                        "ICAO_ID": "KO60C",
                        "LAT_DECIMAL": "43",
                        "LONG_DECIMAL": "-78",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [{"FIX_ID": "KM18K", "LAT_DECIMAL": "41", "LONG_DECIMAL": "-76"}]
            ),
        ],
        ignore_index=True,
    )
    tables["NAV_BASE"] = pd.DataFrame(
        [{"NAV_ID": "KG66K", "LAT_DECIMAL": "42", "LONG_DECIMAL": "-77"}]
    )

    assert flight_plan_path(tables, "E91 KM18K KG66K KO60C") == (
        (40.0, -75.0),
        (41.0, -76.0),
        (42.0, -77.0),
        (43.0, -78.0),
    )
    assert flight_plan_path(tables, "KAAA ALPHA V1 BRAVO KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (36.0, -79.0),
        (35.0, -80.0),
    )


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


def test_waypoint_resolver_uses_column_iteration(tables, monkeypatch):
    def fail_record_materialization(*args, **kwargs):
        raise AssertionError("resolver must not materialize DataFrame records")

    def fail_series_iteration(*args, **kwargs):
        raise AssertionError("resolver must not iterate boxed pandas Series values")

    monkeypatch.setattr(pd.DataFrame, "to_dict", fail_record_materialization)
    monkeypatch.setattr(pd.Series, "__iter__", fail_series_iteration)

    resolver = _WaypointResolver(tables)

    assert resolver.resolve("ALPHA").latitude == 37.0


def test_flight_plan_path_prefers_operational_navaid_over_vot(tables):
    tables["NAV_BASE"] = pd.DataFrame(
        [
            {
                "NAV_ID": "ICT",
                "NAV_TYPE": "VORTAC",
                "LAT_DECIMAL": "37",
                "LONG_DECIMAL": "-97",
            },
            {
                "NAV_ID": "ICT",
                "NAV_TYPE": "VOT",
                "LAT_DECIMAL": "38",
                "LONG_DECIMAL": "-98",
            },
        ]
    )

    assert flight_plan_path(tables, "KAAA ICT KBBB") == (
        (38.0, -77.0),
        (37.0, -97.0),
        (35.0, -80.0),
    )


def test_flight_plan_path_keeps_multiple_operational_navaids_ambiguous(tables):
    tables["NAV_BASE"] = pd.DataFrame(
        [
            {
                "NAV_ID": "ICT",
                "NAV_TYPE": "VOR",
                "LAT_DECIMAL": "37",
                "LONG_DECIMAL": "-97",
            },
            {
                "NAV_ID": "ICT",
                "NAV_TYPE": "VORTAC",
                "LAT_DECIMAL": "38",
                "LONG_DECIMAL": "-98",
            },
            {
                "NAV_ID": "ICT",
                "NAV_TYPE": "VOT",
                "LAT_DECIMAL": "39",
                "LONG_DECIMAL": "-99",
            },
        ]
    )

    with pytest.raises(AmbiguousRecordError, match="Flight-plan waypoint"):
        flight_plan_path(tables, "KAAA ICT KBBB")


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


def _dp_airway_join_tables(tables):
    tables["FIX_BASE"] = pd.DataFrame(
        [
            {"FIX_ID": "MCRAY", "LAT_DECIMAL": "37", "LONG_DECIMAL": "-78"},
            {"FIX_ID": "HAYGR", "LAT_DECIMAL": "36", "LONG_DECIMAL": "-79"},
            {"FIX_ID": "MID", "LAT_DECIMAL": "35", "LONG_DECIMAL": "-80"},
            {"FIX_ID": "LEJOY", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-81"},
        ]
    )
    tables["DP_BASE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "MCRAY",
                "ARTCC": "ZDC",
                "DP_COMPUTER_CODE": "MCRAY2.MCRAY",
            }
        ]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "MCRAY",
                "ARTCC": "ZDC",
                "DP_COMPUTER_CODE": "MCRAY2.MCRAY",
                "ROUTE_PORTION_TYPE": "BODY",
                "BODY_SEQ": "1",
                "POINT_SEQ": sequence,
                "POINT": point,
            }
            for sequence, point in (("10", "MCRAY"), ("20", "HAYGR"))
        ]
    )
    tables["AWY_BASE"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "D",
                "AWY_ID": "178",
                "AWY_DESIGNATION": "RN",
            }
        ]
    )
    tables["AWY_SEG_ALT"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "D",
                "AWY_ID": "178",
                "POINT_SEQ": "10",
                "FROM_POINT": "MCRAY",
                "TO_POINT": "MID",
            },
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "D",
                "AWY_ID": "178",
                "POINT_SEQ": "20",
                "FROM_POINT": "MID",
                "TO_POINT": "LEJOY",
            },
        ]
    )
    return tables


def test_departure_to_adjacent_airway_uses_unique_explicit_filed_join(tables):
    tables = _dp_airway_join_tables(tables)

    assert flight_plan_path(tables, "KAAA MCRAY2.MCRAY DCT Q178 LEJOY KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),  # Explicit MCRAY join; HAYGR is not emitted.
        (35.0, -80.0),
        (34.0, -81.0),
        (35.0, -80.0),
    )
    assert flight_plan_path(tables, "KAAA MCRAY2.MCRAY KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (36.0, -79.0),  # Standalone DP remains complete.
        (35.0, -80.0),
    )


def test_departure_to_airway_without_explicit_connectivity_is_typed(tables):
    tables = _dp_airway_join_tables(tables)
    tables["AWY_SEG_ALT"] = pd.DataFrame(
        [
            {
                "REGULATORY": "Y",
                "AWY_LOCATION": "D",
                "AWY_ID": "178",
                "POINT_SEQ": "10",
                "FROM_POINT": "MID",
                "TO_POINT": "LEJOY",
            }
        ]
    )

    with pytest.raises(RouteConnectivityError) as caught:
        flight_plan_path(tables, "KAAA MCRAY2.MCRAY Q178 LEJOY KBBB")

    error = caught.value
    assert error.entity_type == "Procedure-airway join"
    assert error.procedure_identifier == "MCRAY2.MCRAY"
    assert error.airway_identifier == "Q178"
    assert error.filed_join_identifier == "MCRAY"
    assert error.following_identifier == "LEJOY"
    assert error.candidate_joins == ("MCRAY",)


def test_tokenizer_retains_exact_dotted_departure_computer_code(tables):
    tables["DP_BASE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "EXACT",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "EXACT3.PART",
            }
        ]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "EXACT",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "EXACT3.PART",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "KAAA",
            },
            {
                "DP_NAME": "EXACT",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "EXACT3.PART",
                "BODY_SEQ": "1",
                "POINT_SEQ": "20",
                "POINT": "ALPHA",
            },
        ]
    )

    assert flight_plan_path(tables, "KAAA.EXACT3.PART..KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (35.0, -80.0),
    )


def test_exact_dotted_departure_code_merges_with_trailing_dotted_components(tables):
    """A real ``DP_COMPUTER_CODE`` that itself contains a dot (for example a
    real FAA ``MCRAY2.MCRAY`` code with no standalone ``MCRAY2`` code) must
    still merge as one token even when more dotted components follow it in
    the same unspaced field, since FAA route text routinely dot-chains a DP
    directly into a following airway or fix. Verified against the real
    2024-06-13 NASR cycle: ``KIAD.MCRAY2.MCRAY.LEJOY.KPIT``-shaped text
    previously split ``MCRAY2`` off as its own token (it is not a published
    identifier on its own) and failed with ``RecordNotFoundError`` for
    'MCRAY2', because the tokenizer's ``exact_dp_allowed`` heuristic only
    permitted the merge when no further dotted components followed in the
    same field."""

    tables["DP_BASE"] = pd.DataFrame(
        [{"DP_NAME": "EXACT", "ARTCC": "ZJX", "DP_COMPUTER_CODE": "EXACT3.PART"}]
    )
    tables["DP_RTE"] = pd.DataFrame(
        [
            {
                "DP_NAME": "EXACT",
                "ARTCC": "ZJX",
                "DP_COMPUTER_CODE": "EXACT3.PART",
                "BODY_SEQ": "1",
                "POINT_SEQ": "10",
                "POINT": "ALPHA",
            }
        ]
    )

    assert flight_plan_path(tables, "KAAA.EXACT3.PART.BRAVO.KBBB") == (
        (38.0, -77.0),
        (37.0, -78.0),
        (36.0, -79.0),
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


def test_procedure_body_keeps_only_the_unambiguous_common_portion(tables):
    tables["FIX_BASE"] = pd.concat(
        [
            tables["FIX_BASE"],
            pd.DataFrame(
                [
                    {"FIX_ID": "MERGE", "LAT_DECIMAL": "34", "LONG_DECIMAL": "-79"},
                ]
            ),
        ],
        ignore_index=True,
    )
    tables["STAR_BASE"] = pd.DataFrame(
        [{"STAR_COMPUTER_CODE": "SHARED3", "ARTCC": "ZJX"}]
    )
    tables["STAR_RTE"] = pd.DataFrame(
        [
            {
                "STAR_COMPUTER_CODE": "SHARED3",
                "ARTCC": "ZJX",
                "ROUTE_PORTION_TYPE": "BODY",
                "ROUTE_NAME": route_name,
                "TRANSITION_COMPUTER_CODE": "",
                "BODY_SEQ": "1",
                "POINT_SEQ": sequence,
                "POINT": point,
            }
            for route_name, branch in (
                ("ALPHA BRANCH", "ALPHA"),
                ("BRAVO BRANCH", "BRAVO"),
            )
            for sequence, point in (("10", "KBBB"), ("20", branch), ("30", "MERGE"))
        ]
    )

    assert flight_plan_path(tables, "KAAA SHARED3 KBBB") == (
        (38.0, -77.0),
        (34.0, -79.0),  # The only common inbound body point.
        (35.0, -80.0),
    )


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
    tables["STAR_BASE"] = pd.DataFrame([{"STAR_COMPUTER_CODE": "ARR1", "ARTCC": "ZJX"}])
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

    assert flight_plan_path(tables, "KAAA.DEP1..ALPHA.V1.NAV..ENTRY.ARR1.KBBB") == (
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

    assert _tokenize_flight_plan(tables, "KAAA ALPHA/0354 BBB", resolver=resolver) == (
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
                {
                    "ARPT_ID": name,
                    "ICAO_ID": name,
                    "LAT_DECIMAL": lat,
                    "LONG_DECIMAL": lon,
                }
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
        "STAR_BASE": pd.DataFrame([{"STAR_COMPUTER_CODE": "ARR1", "ARTCC": "ZXX"}]),
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


def test_procedure_index_preserves_procedure_and_dotted_lookup_results():
    tables = _procedure_matrix_tables()
    resolver = _WaypointResolver(tables)
    index = _ProcedureIndex(tables)

    for token in ("DEP1", "DEP1.TRANS", "ARR1", "TRANS.ARR1", "MISSING"):
        assert _procedure_path(
            tables, token, resolver=resolver, procedure_index=index
        ) == _procedure_path(tables, token, resolver=resolver)

    for token in ("DEP1.TRANS", "TRANS.ARR1", "DEP1.MISSING"):
        assert _is_published_dotted_procedure(
            tables, token, procedure_index=index
        ) == _is_published_dotted_procedure(tables, token)


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
