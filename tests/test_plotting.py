from math import radians, tan

import pandas as pd
import pytest
from shapely.geometry import Polygon

import openNASR
import openNASR.plotting as plotting
from openNASR.airport import AirportRecord
from openNASR.airspace import Artcc, ArtccRecord
from openNASR.airway import Airway, AirwayRecord, AirwaySegmentRecord
from openNASR.arrivals import StarProcedure, StarProcedureRecord, StarRouteRecord
from openNASR.ils import IlsRecord
from openNASR.rwy import RunwayRecord
from openNASR import PlottingIndex as PublicPlottingIndex
from openNASR.plotting import (
    PlottingIndex,
    plot_airway,
    plot_artcc,
    plot_airport_procedures,
    plot_airspace,
    plot_flight_plan,
    plot_ils_localizer,
    plot_star,
)


def _artist_coordinates(axes):
    """Return the coordinate payload of every plotted Matplotlib artist."""

    lines = tuple(
        (
            tuple(line.get_xdata()),
            tuple(line.get_ydata()),
        )
        for line in axes.lines
    )
    collections = tuple(
        tuple(tuple(point) for point in collection.get_offsets())
        for collection in axes.collections
    )
    return lines, collections


def _indexed_tables():
    """Small table set exercising every plotting-index source table."""

    return {
        "APT_BASE": pd.DataFrame(
            [
                {
                    "ARPT_ID": " AAA ",
                    "ICAO_ID": "KAAA",
                    "LAT_DECIMAL": "10",
                    "LONG_DECIMAL": "20",
                },
                {
                    "ARPT_ID": "BBB",
                    "ICAO_ID": "KBBB",
                    "LAT_DECIMAL": "11",
                    "LONG_DECIMAL": "21",
                },
                # Invalid coordinates must remain excluded from lookups.
                {
                    "ARPT_ID": "BAD",
                    "ICAO_ID": "KBAD",
                    "LAT_DECIMAL": "not-a-number",
                    "LONG_DECIMAL": "30",
                },
            ]
        ),
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "ONE", "LAT_DECIMAL": "10", "LONG_DECIMAL": "20"},
                {"FIX_ID": "TWO", "LAT_DECIMAL": "11", "LONG_DECIMAL": "21"},
                # Duplicate identifiers are intentionally ambiguous.
                {"FIX_ID": "DUP", "LAT_DECIMAL": "10", "LONG_DECIMAL": "20"},
                {"FIX_ID": "DUP", "LAT_DECIMAL": "11", "LONG_DECIMAL": "21"},
                {"FIX_ID": "BAD", "LAT_DECIMAL": "bad", "LONG_DECIMAL": "30"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(
            [
                {"NAV_ID": "NAV", "LAT_DECIMAL": "10", "LONG_DECIMAL": "20"},
                {"NAV_ID": "DUP", "LAT_DECIMAL": "10", "LONG_DECIMAL": "20"},
            ]
        ),
        "AWY_BASE": pd.DataFrame(
            [
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                    "AWY_DESIGNATION": "V",
                },
                # The final duplicate designation is the source-order winner.
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                    "AWY_DESIGNATION": "J",
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
                    "AWY_ID": "1",
                },
                {
                    "FROM_POINT": "DUP",
                    "TO_POINT": "TWO",
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "D",
                    "AWY_ID": "1",
                },
            ]
        ),
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "10",
                    "LONG_DECIMAL": "20",
                },
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "11",
                    "LONG_DECIMAL": "21",
                },
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "02/20",
                    "LAT_DECIMAL": "12",
                    "LONG_DECIMAL": "22",
                },
            ]
        ),
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
            [
                {
                    "ARPT_ID": "AAA",
                    "STAR_COMPUTER_CODE": "ARR1",
                    "ARTCC": "Z",
                }
            ]
        ),
        "STAR_RTE": pd.DataFrame(
            [
                {
                    "STAR_COMPUTER_CODE": "ARR1",
                    "ARTCC": "Z",
                    "POINT": "NAV",
                    "NEXT_POINT": "TWO",
                }
            ]
        ),
    }


def _plot_all_layers(tables, index):
    figure, axes = plot_airport_procedures(tables, "AAA", index=index)
    return figure, axes


@pytest.fixture(autouse=True)
def _close_matplotlib_figures():
    yield
    try:
        from matplotlib import pyplot as plt
    except ImportError:
        return
    plt.close("all")


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


def test_plotting_index_preserves_line_and_collection_coordinate_data():
    """An indexed render must preserve every artist's underlying coordinates."""

    pytest.importorskip("matplotlib").use("Agg")
    tables = _indexed_tables()
    boundary = Polygon([(19, 9), (100, 9), (100, 13), (19, 13)])

    plain_airspace = plot_airspace(
        tables,
        boundary,
        plot_legend=False,
    )
    indexed_airspace = plot_airspace(
        tables,
        boundary,
        plot_legend=False,
        index=PlottingIndex(tables),
    )
    assert _artist_coordinates(plain_airspace[1]) == _artist_coordinates(
        indexed_airspace[1]
    )

    plain_procedures = _plot_all_layers(tables, None)
    indexed_procedures = _plot_all_layers(tables, PlottingIndex(tables))
    assert _artist_coordinates(plain_procedures[1]) == _artist_coordinates(
        indexed_procedures[1]
    )
    # Runway grouping keeps source order and uses only the first two endpoints;
    # the one-ended 02/20 runway is not rendered. The duplicate FIX endpoint
    # is ambiguous, so only ONE->TWO is rendered, and the final AWY_BASE row
    # wins (J = high altitude).
    assert len(plain_procedures[1].lines) == 3
    assert tuple(plain_procedures[1].lines[0].get_xdata()) == (20.0, 21.0)
    assert tuple(plain_procedures[1].lines[0].get_ydata()) == (10.0, 11.0)
    assert len(plain_airspace[1].lines) == 10
    assert plain_airspace[1].lines[-1].get_color() == "tab:red"

    plain_route = plot_flight_plan(tables, "KAAA DCT KBBB", plot_legend=False)
    indexed_route = plot_flight_plan(
        tables,
        "KAAA DCT KBBB",
        plot_legend=False,
        index=PlottingIndex(tables),
    )
    assert _artist_coordinates(plain_route[1]) == _artist_coordinates(indexed_route[1])


def test_plotting_index_is_public_and_plot_functions_accept_keyword_index():
    import inspect

    assert PublicPlottingIndex is PlottingIndex
    assert openNASR.plot_airway is plot_airway
    assert openNASR.plot_artcc is plot_artcc
    assert openNASR.plot_star is plot_star
    for function in (
        plot_airspace,
        plot_airway,
        plot_artcc,
        plot_airport_procedures,
        plot_flight_plan,
        plot_star,
    ):
        parameter = inspect.signature(function).parameters["index"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        projection = inspect.signature(function).parameters["projection"]
        assert projection.kind is inspect.Parameter.KEYWORD_ONLY


def test_all_public_plotters_support_epsg_3857_web_mercator():
    pytest.importorskip("matplotlib").use("Agg")
    tables = _indexed_tables()
    index = PlottingIndex(tables)
    boundary = Polygon([(19, 9), (22, 9), (22, 12), (19, 12)])
    airway = Airway(
        AirwayRecord({"AWY_ID": "V1"}),
        (AirwaySegmentRecord({"FROM_POINT": "ONE", "TO_POINT": "TWO"}),),
    )
    star = StarProcedure(
        StarProcedureRecord({"STAR_COMPUTER_CODE": "ARR1"}),
        (),
        (StarRouteRecord({"POINT": "NAV", "NEXT_POINT": "TWO"}),),
    )
    artcc = Artcc(ArtccRecord({"LOCATION_ID": "ZXX"}), {"high": boundary})

    calls = (
        lambda: plot_airspace(
            tables,
            boundary,
            plot_high_airways=False,
            plot_low_airways=False,
            plot_airports=False,
            plot_fixes=False,
            plot_airnavs=False,
            plot_legend=False,
            projection="web_mercator",
            index=index,
        ),
        lambda: plot_airway(
            tables,
            airway,
            projection="web_mercator",
            plot_legend=False,
            index=index,
        ),
        lambda: plot_star(
            tables,
            star,
            projection="web_mercator",
            plot_legend=False,
            index=index,
        ),
        lambda: plot_artcc(
            tables,
            artcc,
            plot_high_airways=False,
            plot_low_airways=False,
            plot_airports=False,
            plot_fixes=False,
            plot_airnavs=False,
            plot_legend=False,
            projection="web_mercator",
            index=index,
        ),
        lambda: plot_airport_procedures(
            tables,
            "AAA",
            projection="web_mercator",
            plot_legend=False,
            index=index,
        ),
        lambda: plot_flight_plan(
            tables,
            "KAAA DCT KBBB",
            projection="web_mercator",
            plot_legend=False,
            index=index,
        ),
    )

    for call in calls:
        _, axes = call()
        assert axes.get_xlabel() == "Web Mercator X (m)"
        assert axes.get_ylabel() == "Web Mercator Y (m)"
        assert axes.lines


def test_web_mercator_matches_epsg_3857_reference_coordinates():
    pytest.importorskip("matplotlib").use("Agg")
    tables = _indexed_tables()

    _, axes = plot_flight_plan(
        tables,
        "KAAA DCT KBBB",
        projection="web_mercator",
        plot_legend=False,
    )

    assert axes.lines[0].get_xdata()[0] == pytest.approx(2_226_389.8158654715)
    assert axes.lines[0].get_ydata()[0] == pytest.approx(1_118_889.9748579597)


def test_web_mercator_rejects_conflicting_centered_projection_options():
    boundary = Polygon([(19, 9), (22, 9), (22, 12), (19, 12)])

    with pytest.raises(ValueError, match="different projection"):
        plot_airspace({}, boundary, project_to_nm=True, projection="web_mercator")
    with pytest.raises(ValueError, match="not used"):
        plot_airspace(
            {},
            boundary,
            projection="web_mercator",
            projection_center=(10, 20),
        )
    with pytest.raises(ValueError, match="projection must be"):
        plot_airspace({}, boundary, projection="unknown")


def test_domain_plot_methods_delegate_to_shared_plotting_behavior():
    pytest.importorskip("matplotlib").use("Agg")
    tables = _indexed_tables()
    index = PlottingIndex(tables)

    airport = AirportRecord({"ARPT_ID": "AAA"})
    airport_figure, airport_axes = airport.plot(tables, plot_legend=False, index=index)
    assert airport_figure is airport_axes.figure
    assert len(airport_axes.lines) == 3
    assert airport_axes.get_title() == "AAA procedures"

    airway = Airway(
        AirwayRecord({"REGULATORY": "Y", "AWY_LOCATION": "D", "AWY_ID": "V1"}),
        (
            AirwaySegmentRecord({"FROM_POINT": "ONE", "TO_POINT": "TWO"}),
            AirwaySegmentRecord({"FROM_POINT": "DUP", "TO_POINT": "TWO"}),
        ),
    )
    airway_figure, airway_axes = airway.plot(tables, plot_legend=False, index=index)
    assert airway_figure is airway_axes.figure
    assert len(airway_axes.lines) == 1
    assert tuple(airway_axes.lines[0].get_xdata()) == (20.0, 21.0)
    assert airway_axes.get_title() == "V1 airway"

    star = StarProcedure(
        StarProcedureRecord({"ARRIVAL_NAME": "ARRIVAL", "STAR_COMPUTER_CODE": "ARR1"}),
        (),
        (
            StarRouteRecord({"POINT": "NAV", "NEXT_POINT": "TWO"}),
            StarRouteRecord({"POINT": "DUP", "NEXT_POINT": "TWO"}),
        ),
    )
    star_figure, star_axes = star.plot(
        tables, project_to_nm=True, plot_legend=False, index=index
    )
    assert star_figure is star_axes.figure
    assert len(star_axes.lines) == 1
    assert star_axes.get_xlabel() == "East (NM)"
    assert star_axes.get_title() == "ARRIVAL arrival"

    artcc = Artcc(
        ArtccRecord({"LOCATION_ID": "ZXX"}),
        {"high": Polygon([(19, 9), (22, 9), (22, 12), (19, 12)])},
    )
    artcc_figure, artcc_axes = artcc.plot(
        tables,
        plot_high_airways=False,
        plot_low_airways=False,
        plot_airports=False,
        plot_fixes=False,
        plot_airnavs=False,
        plot_legend=False,
        index=index,
    )
    assert artcc_figure is artcc_axes.figure
    assert len(artcc_axes.lines) == 1
    assert artcc_axes.get_title() == "ZXX high-altitude ARTCC"


def test_domain_plot_helpers_validate_object_and_boundary_selection():
    with pytest.raises(TypeError, match="Airway"):
        plot_airway({}, object())
    with pytest.raises(TypeError, match="StarProcedure"):
        plot_star({}, object())
    with pytest.raises(ValueError, match="level"):
        plot_artcc({}, Artcc(ArtccRecord({}), {}), level="surface")
    with pytest.raises(ValueError, match="no 'low' boundary"):
        plot_artcc({}, Artcc(ArtccRecord({}), {}), level="low")


def test_plotting_index_lookups_match_source_ordered_vectorized_filters():
    tables = _indexed_tables()
    index = PlottingIndex(tables)

    # Coordinate indexes retain all valid rows for each normalized identifier,
    # including duplicate rows and source order, while invalid coordinates are
    # skipped exactly as the direct boolean-mask implementation does.
    for table, column in (("FIX_BASE", "FIX_ID"), ("NAV_BASE", "NAV_ID")):
        frame = tables[table]
        for identifier in ("ONE", "DUP", "MISSING"):
            mask = frame[column].astype(str).str.strip().str.upper().eq(identifier)
            expected = {}
            for row in frame.loc[mask].itertuples(index=False):
                try:
                    point = (float(row.LONG_DECIMAL), float(row.LAT_DECIMAL))
                except (TypeError, ValueError):
                    continue
                expected.setdefault(identifier, []).append(point)
            assert index.coordinates(frame, column).get(identifier, []) == expected.get(
                identifier, []
            )

    assert index.point_coordinates("APT_BASE") == ((20.0, 10.0), (21.0, 11.0))
    assert len(index.navigation_endpoints()["DUP"]) == 3
    assert index.airport_projection_center("AAA") == (10.0, 20.0)
    assert index.airway_segments()[0][0] == "high"
    assert tuple(index.airway_segments()[0][1].coords) == ((20.0, 10.0), (21.0, 11.0))
    departure = index.procedure_segments(
        "AAA", "DP_APT", "DP_RTE", ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE")
    )
    arrival = index.procedure_segments(
        "AAA", "STAR_APT", "STAR_RTE", ("STAR_COMPUTER_CODE", "ARTCC")
    )
    assert tuple(departure[0].coords) == ((20.0, 10.0), (21.0, 11.0))
    reversed_departure = index.procedure_segments(
        "AAA",
        "DP_APT",
        "DP_RTE",
        ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE"),
        reverse=True,
    )
    assert tuple(reversed_departure[0].coords) == ((21.0, 11.0), (20.0, 10.0))
    assert tuple(arrival[0].coords) == ((20.0, 10.0), (21.0, 11.0))
    assert tuple(index.runway_segments("AAA")[0].coords) == (
        (20.0, 10.0),
        (21.0, 11.0),
    )


def test_plotting_index_connects_airway_across_coordinate_less_border_points():
    tables = {
        "FIX_BASE": pd.DataFrame(
            [
                {"FIX_ID": "WEST", "LAT_DECIMAL": "42", "LONG_DECIMAL": "-83"},
                {"FIX_ID": "EAST", "LAT_DECIMAL": "42", "LONG_DECIMAL": "-81"},
            ]
        ),
        "NAV_BASE": pd.DataFrame(),
        "AWY_BASE": pd.DataFrame(
            [
                {
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "C",
                    "AWY_ID": "J554",
                    "AWY_DESIGNATION": "J",
                }
            ]
        ),
        "AWY_SEG_ALT": pd.DataFrame(
            [
                {
                    "FROM_POINT": "WEST",
                    "TO_POINT": "U.S. CANADIAN BORDER-2",
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "C",
                    "AWY_ID": "J554",
                },
                {
                    "FROM_POINT": "U.S. CANADIAN BORDER-2",
                    "TO_POINT": "U.S. CANADIAN BORDER-3",
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "C",
                    "AWY_ID": "J554",
                },
                {
                    "FROM_POINT": "U.S. CANADIAN BORDER-3",
                    "TO_POINT": "EAST",
                    "REGULATORY": "Y",
                    "AWY_LOCATION": "C",
                    "AWY_ID": "J554",
                },
            ]
        ),
    }

    segments = PlottingIndex(tables).airway_segments()

    assert len(segments) == 1
    assert segments[0][0] == "high"
    assert tuple(segments[0][1].coords) == ((-83.0, 42.0), (-81.0, 42.0))


def test_plotting_index_reuses_one_route_resolver(monkeypatch):
    tables = _indexed_tables()
    index = PlottingIndex(tables)
    calls = 0
    original_init = plotting.RouteResolver.__init__

    def tracked_init(self, route_tables):
        nonlocal calls
        calls += 1
        original_init(self, route_tables)

    monkeypatch.setattr(plotting.RouteResolver, "__init__", tracked_init)
    expected = ((10.0, 20.0), (11.0, 21.0))
    assert index.flight_plan_path("KAAA DCT KBBB") == expected
    assert index.flight_plan_path("KAAA DCT KBBB") == expected
    assert calls == 1


def test_plotting_index_handles_sparse_tables_and_missing_columns():
    pytest.importorskip("matplotlib").use("Agg")
    sparse = {
        "APT_BASE": pd.DataFrame([{"LAT_DECIMAL": "1", "LONG_DECIMAL": "2"}]),
        "FIX_BASE": pd.DataFrame([{"FIX_ID": "NO_COORDINATES"}]),
        "AWY_SEG_ALT": pd.DataFrame([{"FROM_POINT": "A"}]),
    }
    index = PlottingIndex(sparse)
    boundary = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)])
    _, axes = plot_airspace(
        sparse,
        boundary,
        plot_legend=False,
        index=index,
    )
    assert len(axes.lines) == 2

    _, procedure_axes = plot_airport_procedures(
        sparse,
        "MISSING",
        plot_legend=False,
        index=index,
    )
    assert len(procedure_axes.lines) == 0


def test_plotting_index_reuse_avoids_full_table_record_conversion(monkeypatch):
    """A prebuilt index supports repeated renders without table-wide ``to_dict``."""

    pytest.importorskip("matplotlib").use("Agg")
    tables = _indexed_tables()
    index = PlottingIndex(tables)

    def fail_full_table_conversion(*_args, **_kwargs):
        raise AssertionError("plotting performed a full-table record conversion")

    monkeypatch.setattr(pd.DataFrame, "to_dict", fail_full_table_conversion)
    monkeypatch.setattr(
        plotting,
        "_coordinates",
        lambda *_args, **_kwargs: pytest.fail(
            "indexed plotting rebuilt navigation coordinates"
        ),
    )
    boundary = Polygon([(19, 9), (23, 9), (23, 13), (19, 13)])
    for _ in range(2):
        plot_airspace(tables, boundary, plot_legend=False, index=index)
        plot_airport_procedures(tables, "AAA", plot_legend=False, index=index)
        plot_flight_plan(tables, "KAAA DCT KBBB", plot_legend=False, index=index)


def test_plotting_index_is_snapshot_scoped_and_rejects_other_tables():
    pytest.importorskip("matplotlib").use("Agg")
    tables = _indexed_tables()
    index = PlottingIndex(tables)
    boundary = Polygon([(19, 9), (100, 9), (100, 13), (19, 13)])

    # Index construction snapshots coordinate values. Mutating source tables
    # requires a new index, matching RouteResolver's snapshot contract. Build
    # the relevant point cache once before mutation; other components remain
    # intentionally lazy.
    plot_airspace(
        tables,
        boundary,
        plot_airports=False,
        plot_airnavs=False,
        plot_high_airways=False,
        plot_low_airways=False,
        plot_legend=False,
        index=index,
    )
    tables["FIX_BASE"].loc[0, "LONG_DECIMAL"] = "99"
    _, old_axes = plot_airspace(
        tables,
        boundary,
        plot_airports=False,
        plot_airnavs=False,
        plot_high_airways=False,
        plot_low_airways=False,
        plot_legend=False,
        index=index,
    )
    _, new_axes = plot_airspace(
        tables,
        boundary,
        plot_airports=False,
        plot_airnavs=False,
        plot_high_airways=False,
        plot_low_airways=False,
        plot_legend=False,
        index=PlottingIndex(tables),
    )
    assert tuple(old_axes.lines[1].get_xdata()) == (20.0,)
    assert tuple(new_axes.lines[1].get_xdata()) == (99.0,)

    other_tables = dict(tables)
    other_tables["FIX_BASE"] = tables["FIX_BASE"].copy()
    with pytest.raises((TypeError, ValueError), match="index|table|snapshot"):
        plot_airspace(
            other_tables,
            boundary,
            plot_legend=False,
            index=index,
        )


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


def test_plot_airspace_projects_to_nautical_miles_about_its_center():
    pytest.importorskip("matplotlib").use("Agg")
    boundary = Polygon([(-76, 39), (-74, 39), (-74, 41), (-76, 41)])
    tables = {
        "APT_BASE": pd.DataFrame(
            [{"ARPT_ID": "CENTER", "LAT_DECIMAL": "40", "LONG_DECIMAL": "-75"}]
        )
    }

    _, axes = plot_airspace(
        tables,
        boundary,
        plot_high_airways=False,
        plot_low_airways=False,
        plot_fixes=False,
        plot_airnavs=False,
        project_to_nm=True,
    )

    assert axes.get_xlabel() == "East (NM)"
    assert axes.get_ylabel() == "North (NM)"
    assert axes.lines[1].get_xdata()[0] == pytest.approx(0.0)
    assert axes.lines[1].get_ydata()[0] == pytest.approx(0.0)


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
    assert [item.get_text() for item in axes.get_legend().get_texts()] == [
        "Flight plan"
    ]


def test_plot_flight_plan_projects_to_nm_about_an_explicit_center():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_BASE": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "ICAO_ID": "KAAA",
                    "LAT_DECIMAL": "40",
                    "LONG_DECIMAL": "-75",
                },
                {
                    "ARPT_ID": "BBB",
                    "ICAO_ID": "KBBB",
                    "LAT_DECIMAL": "41",
                    "LONG_DECIMAL": "-74",
                },
            ]
        ),
        "FIX_BASE": pd.DataFrame(),
        "NAV_BASE": pd.DataFrame(),
    }

    _, axes = plot_flight_plan(
        tables,
        "KAAA DCT KBBB",
        project_to_nm=True,
        projection_center=(40, -75),
    )

    assert axes.get_xlabel() == "East (NM)"
    assert axes.get_ylabel() == "North (NM)"
    assert axes.lines[0].get_xdata()[0] == pytest.approx(0.0)
    assert axes.lines[0].get_ydata()[0] == pytest.approx(0.0)


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
    assert [item.get_text() for item in axes.get_legend().get_texts()] == [
        "Runways",
        "Departures",
        "Arrivals",
    ]


def test_plot_airport_procedures_can_select_individual_layers():
    pytest.importorskip("matplotlib").use("Agg")
    tables = _indexed_tables()
    index = PlottingIndex(tables)

    expected = (
        ({"plot_departures": False, "plot_arrivals": False}, "black"),
        ({"plot_runways": False, "plot_arrivals": False}, "tab:blue"),
        ({"plot_runways": False, "plot_departures": False}, "tab:green"),
    )
    for options, color in expected:
        _, axes = plot_airport_procedures(
            tables,
            "AAA",
            plot_legend=False,
            index=index,
            **options,
        )
        assert len(axes.lines) == 1
        assert axes.lines[0].get_color() == color


def test_plot_airport_procedures_projects_to_nm_about_the_airport():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_BASE": pd.DataFrame(
            [{"ARPT_ID": "AAA", "LAT_DECIMAL": "40", "LONG_DECIMAL": "-75"}]
        ),
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "40",
                    "LONG_DECIMAL": "-75",
                },
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "40.01",
                    "LONG_DECIMAL": "-75",
                },
            ]
        ),
    }

    _, axes = plot_airport_procedures(tables, "AAA", project_to_nm=True)

    assert axes.get_xlabel() == "East (NM)"
    assert axes.get_ylabel() == "North (NM)"
    assert axes.lines[0].get_xdata()[0] == pytest.approx(0.0)
    assert axes.lines[0].get_ydata()[0] == pytest.approx(0.0)


def test_plot_ils_localizer_draws_standard_threshold_wedge():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_END_ID": "36",
                    "LAT_DECIMAL": "40",
                    "LONG_DECIMAL": "-75",
                }
            ]
        )
    }
    localizer = {
        "ARPT_ID": "AAA",
        "RWY_END_ID": "36",
        "LAT_DECIMAL": "40.01",
        "LONG_DECIMAL": "-75",
        "APCH_BEAR": "0",
        "MAG_VAR": "0",
        "MAG_VAR_HEMIS": "E",
    }

    _, axes = IlsRecord(localizer).plot(
        tables,
        projection="nautical_miles",
        wedge_distance_nm=20,
    )

    vertices = axes.patches[0].get_xy()
    threshold_half_width_nm = 350 / 6076.12
    far_half_width_nm = threshold_half_width_nm + 20 * tan(radians(2.5))
    assert vertices[0] == pytest.approx((-threshold_half_width_nm, 0))
    assert vertices[1] == pytest.approx((-far_half_width_nm, -20))
    assert vertices[2] == pytest.approx((far_half_width_nm, -20))
    assert vertices[3] == pytest.approx((threshold_half_width_nm, 0))
    assert vertices[4] == pytest.approx(vertices[0])
    assert [text.get_text() for text in axes.get_legend().get_texts()] == [
        "Localizer",
        "Localizer course",
    ]


def test_runway_record_plot_draws_selected_surveyed_runway():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "40",
                    "LONG_DECIMAL": "-75",
                },
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "40.01",
                    "LONG_DECIMAL": "-75",
                },
            ]
        )
    }
    runway = RunwayRecord({"ARPT_ID": "AAA", "RWY_ID": "01/19"})

    _, axes = runway.plot(tables)

    assert len(axes.lines) == 1
    assert tuple(axes.lines[0].get_xdata()) == pytest.approx((-75, -75))
    assert tuple(axes.lines[0].get_ydata()) == pytest.approx((40, 40.01))
    assert axes.lines[0].get_linewidth() == pytest.approx(4)


def test_usgs_basemap_is_available_from_modern_plotting_methods(monkeypatch):
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_BASE": pd.DataFrame(
            [{"ARPT_ID": "AAA", "LAT_DECIMAL": "40", "LONG_DECIMAL": "-75"}]
        ),
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "40",
                    "LONG_DECIMAL": "-75",
                },
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "01/19",
                    "LAT_DECIMAL": "40.01",
                    "LONG_DECIMAL": "-75",
                },
            ]
        ),
    }
    calls = []
    monkeypatch.setattr(
        plotting,
        "_add_usgs_imagery_background",
        lambda axes: calls.append(axes),
    )

    runway = RunwayRecord({"ARPT_ID": "AAA", "RWY_ID": "01/19"})
    runway.plot(tables, projection="web_mercator", basemap="usgs_imagery")
    AirportRecord({"ARPT_ID": "AAA"}).plot(
        tables,
        projection="web_mercator",
        basemap="usgs_imagery",
        plot_departures=False,
        plot_arrivals=False,
    )

    assert len(calls) == 2
    with pytest.raises(ValueError, match="requires projection='web_mercator'"):
        runway.plot(tables, basemap="usgs_imagery")


def test_plot_ils_localizer_can_hide_wedge_and_reject_invalid_distance():
    pytest.importorskip("matplotlib").use("Agg")
    tables = {
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_END_ID": "36",
                    "LAT_DECIMAL": "40",
                    "LONG_DECIMAL": "-75",
                }
            ]
        )
    }
    localizer = {
        "ARPT_ID": "AAA",
        "RWY_END_ID": "36",
        "LAT_DECIMAL": "40.01",
        "LONG_DECIMAL": "-75",
        "APCH_BEAR": "0",
        "MAG_VAR": "0",
        "MAG_VAR_HEMIS": "E",
    }

    _, axes = plot_ils_localizer(tables, localizer, plot_wedge=False)
    assert not axes.patches
    with pytest.raises(ValueError, match="greater than zero"):
        plot_ils_localizer(tables, localizer, wedge_distance_nm=0)


def test_ils_record_plot_draws_top_and_side_glide_slope_views():
    pytest.importorskip("matplotlib").use("Agg")
    from matplotlib import pyplot as plt

    tables = {
        "APT_RWY_END": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "18/36",
                    "RWY_END_ID": "36",
                    "LAT_DECIMAL": "40",
                    "LONG_DECIMAL": "-75",
                    "RWY_END_ELEV": "100",
                },
                {
                    "ARPT_ID": "AAA",
                    "RWY_ID": "18/36",
                    "RWY_END_ID": "18",
                    "LAT_DECIMAL": "40.01",
                    "LONG_DECIMAL": "-75",
                    "RWY_END_ELEV": "105",
                },
            ]
        ),
        "ILS_GS": pd.DataFrame(
            [
                {
                    "ARPT_ID": "AAA",
                    "RWY_END_ID": "36",
                    "ILS_LOC_ID": "I-AAA",
                    "LAT_DECIMAL": "39.999",
                    "LONG_DECIMAL": "-75",
                    "SITE_ELEVATION": "110",
                    "G_S_ANGLE": "3",
                }
            ]
        ),
    }
    localizer = IlsRecord(
        {
            "ARPT_ID": "AAA",
            "RWY_END_ID": "36",
            "ILS_LOC_ID": "I-AAA",
            "LAT_DECIMAL": "40.01",
            "LONG_DECIMAL": "-75",
            "APCH_BEAR": "0",
            "MAG_VAR": "0",
            "MAG_VAR_HEMIS": "E",
        }
    )
    figure, (top_axes, side_axes) = plt.subplots(1, 2)

    returned_figure, returned_axes = localizer.plot(
        tables,
        axes=top_axes,
        side_axes=side_axes,
        projection="nautical_miles",
    )

    assert returned_figure is figure
    assert returned_axes is top_axes
    assert len(top_axes.collections) == 2
    assert len(top_axes.patches) == 1
    assert len(side_axes.lines) == 3
    assert [line.get_label() for line in side_axes.lines[:2]] == [
        "Runway",
        "3° glide slope",
    ]
    assert side_axes.get_xlabel() == "NM from runway threshold"
    assert side_axes.get_ylabel() == "Elevation (ft MSL)"
