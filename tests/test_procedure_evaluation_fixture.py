"""The cycle-pinned procedure evaluation set has stable expected joins."""

import json
from pathlib import Path


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
