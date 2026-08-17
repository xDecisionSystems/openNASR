"""Render an airport's runways and ILS localizer approach lines.

Run from the repository root after installing the plotting extra:

    python tests/main_test_NASR_airport_runways_ils.py --airport ATL
"""

from __future__ import annotations

import argparse
from math import cos, radians, sin
from pathlib import Path

from openNASR.cfcn import ll2xy, xy2ll


# Set to False to render in longitude/latitude instead of east/north NM.
PLOT_IN_NAUTICAL_MILES = True
ILS_APPROACH_LENGTH_NM = 20.0


def _airport_center(nasr, airport_id: str) -> tuple[float, float]:
    airports = nasr["APT_BASE"]
    rows = airports[airports["ARPT_ID"].str.strip().str.upper() == airport_id]
    if len(rows) != 1:
        raise ValueError(f"Expected one FAA airport record for {airport_id!r}")
    row = rows.iloc[0]
    return float(row["LAT_DECIMAL"]), float(row["LONG_DECIMAL"])


def _true_bearing(row) -> float:
    """Return the published ILS inbound course after magnetic correction."""

    magnetic_variation = float(row["MAG_VAR"] or 0)
    if str(row["MAG_VAR_HEMIS"]).strip().upper() == "W":
        magnetic_variation = -magnetic_variation
    return (float(row["APCH_BEAR"]) + magnetic_variation) % 360


def _display_coordinates(
    latitudes, longitudes, center: tuple[float, float]
) -> tuple[object, object]:
    if PLOT_IN_NAUTICAL_MILES:
        x_values, y_values, _, _ = ll2xy(latitudes, longitudes, llc=center)
        return x_values, y_values
    return longitudes, latitudes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot an airport's runways and ILS localizer approach lines."
    )
    parser.add_argument("--airport", default="ATL", help="FAA airport identifier")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("airport_runways_ils.png"),
        help="PNG path to write (default: %(default)s)",
    )
    parser.add_argument("--show", action="store_true", help="Open the plot window")
    args = parser.parse_args()
    airport_id = args.airport.strip().upper()

    import matplotlib

    if not args.show:
        matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    from openNASR import NASR

    nasr = NASR()
    center = _airport_center(nasr, airport_id)
    figure, axes = plt.subplots()

    runway_ends = nasr["APT_RWY_END"]
    runway_ends = runway_ends[
        runway_ends["ARPT_ID"].str.strip().str.upper() == airport_id
    ]
    plotted_runways = False
    for _runway_id, ends in runway_ends.groupby("RWY_ID", sort=True):
        if len(ends) < 2:
            continue
        x_values, y_values = _display_coordinates(
            ends["LAT_DECIMAL"].astype(float),
            ends["LONG_DECIMAL"].astype(float),
            center,
        )
        axes.plot(
            x_values,
            y_values,
            color="black",
            linewidth=3,
            label=None if plotted_runways else "Runways",
        )
        plotted_runways = True

    ils_rows = nasr["ILS_BASE"]
    ils_rows = ils_rows[ils_rows["ARPT_ID"].str.strip().str.upper() == airport_id]
    plotted_ils = False
    for row in ils_rows.to_dict(orient="records"):
        try:
            latitude, longitude = float(row["LAT_DECIMAL"]), float(row["LONG_DECIMAL"])
            x_start, y_start, _, _ = ll2xy(latitude, longitude, llc=center)
            # The localizer is beyond the runway threshold; extend its reciprocal
            # course outward from the transmitter to show the inbound approach path.
            outbound = radians((_true_bearing(row) + 180) % 360)
        except (KeyError, TypeError, ValueError):
            continue
        x_end = x_start + ILS_APPROACH_LENGTH_NM * sin(outbound)
        y_end = y_start + ILS_APPROACH_LENGTH_NM * cos(outbound)
        if PLOT_IN_NAUTICAL_MILES:
            x_values, y_values = (x_start, x_end), (y_start, y_end)
        else:
            latitude_end, longitude_end = xy2ll(x_end, y_end, llc=center)
            x_values, y_values = (longitude, longitude_end), (latitude, latitude_end)
        axes.plot(
            x_values,
            y_values,
            color="tab:blue",
            linewidth=1.5,
            marker="o",
            markevery=[0],
            label=None if plotted_ils else "ILS approach paths",
        )
        axes.annotate(str(row["RWY_END_ID"]), (x_start, y_start), fontsize=7)
        plotted_ils = True

    if axes.get_legend_handles_labels()[0]:
        axes.legend()
    units = "nautical miles" if PLOT_IN_NAUTICAL_MILES else "longitude/latitude"
    axes.set_title(f"{airport_id}: runways and ILS approach paths ({units})")
    axes.set_xlabel("East (NM)" if PLOT_IN_NAUTICAL_MILES else "Longitude")
    axes.set_ylabel("North (NM)" if PLOT_IN_NAUTICAL_MILES else "Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    figure.savefig(args.output, dpi=200, bbox_inches="tight")
    print(f"wrote {args.output.resolve()} ({len(ils_rows)} ILS approach paths)")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
