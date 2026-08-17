"""Render ZOB with high- and low-altitude FAA airways.

Run from the repository root after installing the plotting extra:

    python plotExamples/main_test_NASR_zob_airways.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from duckdb_example_setup import load_duckdb_nasr


# Set to False to render in longitude/latitude instead of east/north NM.
PLOT_IN_NAUTICAL_MILES = True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot ZOB with high- and low-altitude airways."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "plots" / "zob_high_low_airways.png",
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
    from shapely.ops import unary_union

    from openNASR import plot_airspace

    nasr = load_duckdb_nasr(cycle=args.cycle, cache_dir=args.cache_dir)
    zob = nasr.artccs.get("ZOB")
    boundaries = tuple(
        boundary.getShape for boundary in (zob.high, zob.low) if boundary is not None
    )
    if not boundaries:
        raise RuntimeError("ZOB has no FAA high or low ARTCC boundary")
    boundary = unary_union(boundaries)
    figure, axes = plot_airspace(
        nasr,
        boundary,
        plot_high_airways=True,
        plot_low_airways=True,
        project_to_nm=PLOT_IN_NAUTICAL_MILES,
    )
    units = "nautical miles" if PLOT_IN_NAUTICAL_MILES else "longitude/latitude"
    axes.set_title(f"ZOB: high- and low-altitude airways ({units})")
    figure.savefig(args.output, dpi=200, bbox_inches="tight")
    print(f"wrote {args.output.resolve()} ({len(axes.lines)} line segments)")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
