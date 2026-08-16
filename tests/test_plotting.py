import pandas as pd
import pytest
from shapely.geometry import Polygon

from openNASR.plotting import plot_airspace


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
