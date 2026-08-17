"""The curated route regression sample is tracked and cycle-pinned."""

import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "route_regressions" / "routes.json"


def test_route_regression_fixture_has_one_named_route_per_category():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert fixture["cycle_date"] == "2026-05-14"
    routes = fixture["routes"]
    assert {entry["category"] for entry in routes} == {
        "success",
        "parser error",
        "procedure-resolution error",
        "airway-resolution error",
        "waypoint ambiguity",
        "missing NASR data",
        "malformed input",
    }
    assert len({entry["id"] for entry in routes}) == len(routes)
    assert all(entry["route"].strip() for entry in routes)
