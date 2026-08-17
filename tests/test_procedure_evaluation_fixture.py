"""The cycle-pinned procedure evaluation set has stable expected joins."""

import json
from pathlib import Path

from openNASR.flightplan import RouteResolver, _procedure_path, _tokenize_flight_plan
from test_flightplan import _procedure_matrix_tables

FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "route_regressions"
    / "procedure_evaluation.json"
)


def test_procedure_evaluation_fixture_has_complete_ordered_expectations():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert fixture["cycle_date"] == "2026-05-14"
    assert [case["id"] for case in fixture["routes"]] == [
        "bare_dp",
        "dotted_dp_transition",
        "bare_star",
        "dotted_star_transition",
        "dp_to_airway",
        "airway_to_star",
        "dp_to_airway_to_star",
    ]
    for case in fixture["routes"]:
        assert case["route"]
        assert case["procedures"]
        assert case["connections"]


def test_procedure_evaluation_routes_have_ordered_connections_and_coordinates():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    tables = _procedure_matrix_tables()
    resolver = RouteResolver(tables)

    for case in fixture["routes"]:
        path = resolver.path(case["route"])
        assert path, case["id"]
        tokens = _tokenize_flight_plan(
            tables, case["route"], resolver=resolver._waypoints
        )
        procedures = [
            token.value for token in tokens if token.value in case["procedures"]
        ]
        assert procedures == case["procedures"], case["id"]
        for identifier in case["connections"]:
            assert any(
                point.identifier == identifier
                for token in tokens
                if token.value in case["procedures"]
                for point in (
                    _procedure_path(
                        tables,
                        token.value,
                        resolver=resolver._waypoints,
                    )
                    or ()
                )
            ), (case["id"], identifier)
