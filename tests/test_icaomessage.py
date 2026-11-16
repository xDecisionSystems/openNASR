"""ICAO FPL parsing and the ignored speed/level notes."""

import pandas as pd
import pytest

from openNASR import IcaoMessageError, RouteResolver, parse_icao_flight_plan

FPL = (
    "(FPL-UAL123-IS-B738/M-SDE2FGHIRWY/LB1-KAAA1530-N0450F350 ALPHA DCT BRAVO "
    "-KBBB0210 KCCC-PBN/A1 REG/N12345)"
)


@pytest.fixture
def tables():
    def airport(arpt, icao, lat, lon):
        return {
            "ARPT_ID": arpt,
            "ICAO_ID": icao,
            "LAT_DECIMAL": lat,
            "LONG_DECIMAL": lon,
        }

    return {
        "APT_BASE": pd.DataFrame(
            [airport("AAA", "KAAA", "38", "-77"), airport("BBB", "KBBB", "35", "-80")]
        ),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "ALPHA", "LAT_DECIMAL": "37", "LONG_DECIMAL": "-78"},
                {"FIX_ID": "BRAVO", "LAT_DECIMAL": "36", "LONG_DECIMAL": "-79"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(),
    }


def test_the_route_departure_and_destination_are_extracted():
    plan = parse_icao_flight_plan(FPL)

    assert plan.message_type == "FPL"
    assert plan.aircraft_id == "UAL123"
    assert (plan.departure, plan.destination) == ("KAAA", "KBBB")
    assert plan.route_field == "N0450F350 ALPHA DCT BRAVO"
    assert plan.route == "KAAA ALPHA DCT BRAVO KBBB"


def test_a_message_without_parentheses_or_with_odd_spacing_still_parses():
    plan = parse_icao_flight_plan(
        "FPL-N1-VG-C172/L-S/C-KAAA1200-N0110A055  ALPHA \n BRAVO -KBBB0100"
    )

    assert plan.route == "KAAA ALPHA BRAVO KBBB"


@pytest.mark.parametrize(
    ("message", "fragment"),
    [
        ("", "empty"),
        ("(ARR-UAL123-KAAA-KBBB)", "only FPL"),
        ("(FPL-UAL123-IS-B738/M)", "at least fields"),
        ("(FPL-X-IS-B738/M-S-AA1530-N0450F350 ALPHA-KBBB0210)", "departure"),
        ("(FPL-X-IS-B738/M-S-KAAA1530-N0450F350 ALPHA-KB0210)", "destination"),
        ("(FPL-X-IS-B738/M-S-KAAA1530- -KBBB0210)", "route"),
        ("(FPL-X-IS-B738/M-S-KAAA1530-N0450F350-KBBB0210)", "no route"),
    ],
)
def test_unusable_messages_raise_a_clear_error(message, fragment):
    with pytest.raises(IcaoMessageError, match=fragment):
        parse_icao_flight_plan(message)


def test_resolver_returns_what_it_extracted_with_the_result(tables):
    plan, result = RouteResolver(tables).resolve_icao_message(FPL)

    assert plan.route == "KAAA ALPHA DCT BRAVO KBBB"
    assert result.complete
    assert [p.name for p in result.waypoints] == ["KAAA", "ALPHA", "BRAVO", "KBBB"]


def test_ignored_groups_are_echoed_as_info_and_do_not_make_a_route_incomplete(tables):
    result = RouteResolver(tables).resolve("KAAA ALPHA/N0450F350 BRAVO KBBB/0354")

    assert result.complete
    notes = [(d.token, d.severity, d.detail) for d in result.diagnostics]
    assert notes == [
        ("N0450F350", "info", {"after": "ALPHA"}),
        ("0354", "info", {"after": "KBBB"}),
    ]
    assert result.diagnostics[0].position == len("KAAA ALPHA/")


def test_a_standalone_speed_level_group_is_skipped_not_looked_up(tables):
    result = RouteResolver(tables).resolve("KAAA N0450F350 ALPHA KBBB")

    assert result.complete
    assert [p.name for p in result.waypoints] == ["KAAA", "ALPHA", "KBBB"]
    assert result.diagnostics[0].token == "N0450F350"
