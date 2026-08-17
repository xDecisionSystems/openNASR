import pandas as pd
import pytest
from shapely.geometry import Polygon

from openNASR.plotting import plot_airport_procedures, plot_airspace, plot_flight_plan


def test_plot_airspace_draws_contained_airports_and_intersecting_airways():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_BASE": pd.DataFrame(
            [
                {"ARPT_ID": "IN", "LAT_DECIMAL": "1", "LONG_DECIMAL": "1"},
                {"ARPT_ID": "OUT", "LAT_DECIMAL": "5", "LONG_DECIMAL": "5"},
            ]
        ),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "ONE", "LAT_DECIMAL": "1", "LONG_DECIMAL": "-1"},
                {"FIX_ID": "TWO", "LAT_DECIMAL": "1", "LONG_DECIMAL": "3"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(),
        "AWY_BASE": pd.DataFrame(
            [
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                    "AWY_DESIGNATION": "J",
                }
            ]
        ),
        "AWY_SEG_ALT": pd.DataFrame(
            [
                {
                    "FROM_POINT": "ONE",
                    "TO_POINT": "TWO",
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                }
            ]
        ),
    }

    figure, axes = plot_airspace(tables, Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]))

    assert figure is axes.figure
    assert len(axes.lines) == 3  # boundary, one airport, and one airway segment
    assert list(axes.lines[-1].get_xdata()) == [0.0, 2.0]
    assert list(axes.lines[-1].get_ydata()) == [1.0, 1.0]
    assert [item.get_text() for item in axes.get_legend().get_texts()] == [
        "Airspace",
        "Airports",
        "High-altitude airways",
    ]
    assert axes.lines[1].get_linestyle() == "None"


def test_plot_airspace_visibility_switches_filter_airway_levels_and_points():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_BASE": pd.DataFrame([{"LAT_DECIMAL": "1", "LONG_DECIMAL": "1"}]),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "ONE", "LAT_DECIMAL": "1", "LONG_DECIMAL": "0"},
                {"FIX_ID": "TWO", "LAT_DECIMAL": "1", "LONG_DECIMAL": "2"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(),
        "AWY_BASE": pd.DataFrame(
            [
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "HIGH",
                    "AWY_DESIGNATION": "J",
                },
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "LOW",
                    "AWY_DESIGNATION": "V",
                },
            ]
        ),
        "AWY_SEG_ALT": pd.DataFrame(
            [
                {
                    "FROM_POINT": "ONE",
                    "TO_POINT": "TWO",
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "HIGH",
                },
                {
                    "FROM_POINT": "ONE",
                    "TO_POINT": "TWO",
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "LOW",
                },
            ]
        ),
    }

    _, axes = plot_airspace(
        tables,
        Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
        plot_low_airways=False,
        plot_airports=False,
        plot_fixes=False,
        plot_airnavs=False,
    )

    assert len(axes.lines) == 2  # boundary and the high airway only


def test_plot_airspace_rejects_objects_without_geometry():
    with pytest.raises(TypeError, match="Shapely geometry"):
        plot_airspace({}, object())


def test_plot_airspace_can_hide_its_legend():
    pytest.importorskip("matplotlib").use("Agg")
    _, axes = plot_airspace(
        {"APT_BASE": pd.DataFrame()},
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        plot_legend=False,
    )

    assert axes.get_legend() is None


def test_plot_flight_plan_draws_the_resolved_route():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_BASE": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "ICAO_ID": "KAAA",
                    "LAT_DECIMAL": "1",
                    "LONG_DECIMAL": "2",
                },
                {
                    "ARPT_ID": "BBB",
                    "ICAO_ID": "KBBB",
                    "LAT_DECIMAL": "3",
                    "LONG_DECIMAL": "4",
                },
            ]
        ),
        "FIX_BASE": pd.DataFrame(),
        "NAV_BASE": pd.DataFrame(),
    }

    figure, axes = plot_flight_plan(tables, "KAAA DCT KBBB")

    assert figure is axes.figure
    assert list(axes.lines[0].get_xdata()) == [2.0, 4.0]
    assert list(axes.lines[0].get_ydata()) == [1.0, 3.0]


def test_plot_airport_procedures_draws_runways_departures_and_arrivals():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "0",
                    "LONG_DECIMAL": "0",
                },
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "1",
                    "LONG_DECIMAL": "0",
                },
            ]
        ),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "ONE", "LAT_DECIMAL": "1", "LONG_DECIMAL": "1"},
                {"FIX_ID": "TWO", "LAT_DECIMAL": "2", "LONG_DECIMAL": "2"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(),
        "DP_APT": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "DP_NAME": "DEP",
                    "ARTCC": "Z",
                    "DP_COMPUTER_CODE": "DEP1",
                }
            ]
        ),
        "DP_RTE": pd.DataFrame(
            [
                {
                    "DP_NAME": "DEP",
                    "ARTCC": "Z",
                    "DP_COMPUTER_CODE": "DEP1",
                    "POINT": "ONE",
                    "NEXT_POINT": "TWO",
                }
            ]
        ),
        "STAR_APT": pd.DataFrame(
            [{"ARPT_ID": "AAA", "STAR_COMPUTER_CODE": "ARR1", "ARTCC": "Z"}]
        ),
        "STAR_RTE": pd.DataFrame(
            [
                {
                    "STAR_COMPUTER_CODE": "ARR1",
                    "ARTCC": "Z",
                    "POINT": "TWO",
                    "NEXT_POINT": "ONE",
                }
            ]
        ),
    }

    _, axes = plot_airport_procedures(tables, "AAA")

    assert len(axes.lines) == 3
