"""The builder measures whether DP/STAR rows are stored in flight order."""

import json
import warnings

import pandas as pd
import pytest

from openNASR.cycles import CycleManager
from openNASR.duckdb_builder import duckdb_metadata_path
from openNASR.invariants import (
    FLIGHT_ORDER,
    INSUFFICIENT,
    REVERSED,
    check_procedure_order,
)


def _frames(count: int, *, reverse: bool, airport_end: str):
    """``count`` procedures, each a line of fixes running away from its airport."""

    fixes, airports, dp_rows, dp_apt, star_rows, star_apt = [], [], [], [], [], []
    for n in range(count):
        airport = f"A{n}"
        airports.append(
            {"ARPT_ID": airport, "LAT_DECIMAL": str(n), "LONG_DECIMAL": "0"}
        )
        names = [f"F{n}_{i}" for i in range(4)]
        for i, name in enumerate(names):
            fixes.append(
                {"FIX_ID": name, "LAT_DECIMAL": str(n), "LONG_DECIMAL": str(i + 1)}
            )
        # names[0] is nearest the airport; ``flight`` lists it first for a DP
        # and last for a STAR.
        flight = names if airport_end == "first" else names[::-1]
        stored = flight[::-1] if reverse else flight
        for seq, point in enumerate(stored):
            dp_rows.append(
                {
                    "DP_NAME": f"D{n}",
                    "ARTCC": "Z",
                    "DP_COMPUTER_CODE": f"D{n}",
                    "ROUTE_PORTION_TYPE": "BODY",
                    "ROUTE_NAME": "B",
                    "POINT_SEQ": str(seq * 10),
                    "POINT": point,
                }
            )
            star_rows.append(
                {
                    "STAR_COMPUTER_CODE": f"S{n}",
                    "ARTCC": "Z",
                    "ROUTE_PORTION_TYPE": "BODY",
                    "ROUTE_NAME": "B",
                    "POINT_SEQ": str(seq * 10),
                    "POINT": point,
                }
            )
        dp_apt.append(
            {
                "DP_NAME": f"D{n}",
                "ARTCC": "Z",
                "DP_COMPUTER_CODE": f"D{n}",
                "BODY_NAME": "B",
                "ARPT_ID": airport,
            }
        )
        star_apt.append(
            {
                "STAR_COMPUTER_CODE": f"S{n}",
                "ARTCC": "Z",
                "BODY_NAME": "B",
                "ARPT_ID": airport,
            }
        )
    return {
        "FIX_BASE": pd.DataFrame(fixes),
        "APT_BASE": pd.DataFrame(airports),
        "DP_RTE": pd.DataFrame(dp_rows),
        "DP_APT": pd.DataFrame(dp_apt),
        "STAR_RTE": pd.DataFrame(star_rows),
        "STAR_APT": pd.DataFrame(star_apt),
    }


def _frames_in_real_faa_order(count: int, *, flip: bool):
    """Real FAA convention: DP airport first, STAR airport last."""

    dp = _frames(count, reverse=flip, airport_end="first")
    star = _frames(count, reverse=flip, airport_end="last")
    dp["STAR_RTE"], dp["STAR_APT"] = star["STAR_RTE"], star["STAR_APT"]
    return dp


def test_real_faa_convention_is_reported_as_flight_order():
    result = check_procedure_order(_frames_in_real_faa_order(30, flip=False))

    assert result["status"] == FLIGHT_ORDER
    assert result["dp"]["airport_nearer_first_point"] == 30
    assert result["star"]["airport_nearer_last_point"] == 30


def test_a_flipped_convention_is_detected_for_the_whole_cycle():
    result = check_procedure_order(_frames_in_real_faa_order(30, flip=True))

    assert result["status"] == REVERSED


def test_too_few_procedures_is_not_a_verdict():
    result = check_procedure_order(_frames_in_real_faa_order(5, flip=False))

    assert result["status"] == INSUFFICIENT


def test_build_records_the_check_in_the_sidecar(make_nasr_from_fixture):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    result = CycleManager(cache_root).build_duckdb("2026-08-06")

    sidecar = json.loads(duckdb_metadata_path(result.database_path).read_text("utf-8"))
    assert sidecar["checks"]["procedure_order"]["status"] == INSUFFICIENT


def test_build_warns_when_the_convention_is_not_flight_order():
    from openNASR.duckdb_builder import _warn_on_unexpected_order

    flipped = check_procedure_order(_frames_in_real_faa_order(30, flip=True))
    with pytest.warns(RuntimeWarning, match="not stored in flight order"):
        _warn_on_unexpected_order("2026-10-29", flipped)

    healthy = check_procedure_order(_frames_in_real_faa_order(30, flip=False))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _warn_on_unexpected_order("2026-10-29", healthy)
