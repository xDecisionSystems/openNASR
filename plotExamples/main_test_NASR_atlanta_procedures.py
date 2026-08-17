"""Render ATL runways, departures, and arrivals from the cached FAA cycle.

Run from the repository root after installing the plotting extra:

    python plotExamples/main_test_NASR_atlanta_procedures.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _duckdb import load_duckdb_nasr


# Set to False to render in longitude/latitude instead of east/north NM.
PLOT_IN_NAUTICAL_MILES = True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot ATL airport runways and arrival/departure procedures."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "plots" / "atlanta_airport_procedures.png",
        help="PNG path to write (default: %(default)s)",
    )
    parser.add_argument("--show", action="store_true", help="Open the plot window")
    parser.add_argument("--cycle", help="Exact local NASR cycle (YYYY-MM-DD)")
    parser.add_argument("--cache-dir", type=Path, help="NASR cache directory")
    args = parser.parse_args()

    import matplotlib

    if not args.show:
        matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    from openNASR import plot_airport_procedures

    nasr = load_duckdb_nasr(cycle=args.cycle, cache_dir=args.cache_dir)
    figure, axes = plot_airport_procedures(
        nasr,
        "ATL",
        project_to_nm=PLOT_IN_NAUTICAL_MILES,
        plot_legend=True,
    )
    units = "nautical miles" if PLOT_IN_NAUTICAL_MILES else "longitude/latitude"
    axes.set_title(f"ATL: runways, departures, and arrivals ({units})")
    figure.savefig(args.output, dpi=200, bbox_inches="tight")
    print(f"wrote {args.output.resolve()} ({len(axes.lines)} line segments)")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
