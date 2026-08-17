"""Stable route-shape/report contracts for the non-CI benchmark."""

from benchmarks.run_benchmarks import _is_direct_or_airway_only, _summarize


def test_route_benchmark_separates_procedure_and_direct_shapes():
    assert _is_direct_or_airway_only("KBWI..KDCA/0030")
    assert _is_direct_or_airway_only("KBWI DCT V1 KDCA")
    assert not _is_direct_or_airway_only("KATL.HAALO3.SARGE..KVPS/0048")


def test_route_benchmark_summary_has_stable_statistics():
    summary = _summarize([0.001, 0.002, 0.003, 0.004])

    assert summary["mean"] == 0.0025
    assert summary["median"] == 0.0025
    assert set(summary) == {"mean", "median", "p95", "min", "max"}
