"""Deterministic validation selection does not depend on local route CSVs."""

from pathlib import Path

from tools.route_path_validation import load_routes, select_routes


def test_validation_uses_tracked_fixture_and_seeded_selection():
    fixture = Path(__file__).parent / "fixtures" / "route_regressions" / "routes.json"
    cycle, routes = load_routes(fixture)

    assert cycle == "2026-05-14"
    first = select_routes(routes, seed=20260514, sample_size=3)
    second = select_routes(routes, seed=20260514, sample_size=3)
    assert first == second
    assert len(first) == 3


def test_validation_returns_all_routes_when_sample_is_omitted():
    fixture = Path(__file__).parent / "fixtures" / "route_regressions" / "routes.json"
    _cycle, routes = load_routes(fixture)

    assert select_routes(routes, seed=1, sample_size=None) == routes
