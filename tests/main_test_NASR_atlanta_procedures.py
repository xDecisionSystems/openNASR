"""Render ATL runways, departures, and arrivals from the cached FAA cycle.

Run from the repository root after installing the plotting extra:

    python tests/main_test_NASR_atlanta_procedures.py
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot ATL airport runways and arrival/departure procedures."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("atlanta_airport_procedures.png"),
        help="PNG path to write (default: %(default)s)",
    )
    parser.add_argument("--show", action="store_true", help="Open the plot window")
    args = parser.parse_args()

    import matplotlib

    if not args.show:
        matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    from openNASR import NASR, plot_airport_procedures

    nasr = NASR()
    figure, axes = plot_airport_procedures(nasr, "ATL")
    axes.set_title("ATL: runways, departures, and arrivals")
    figure.savefig(args.output, dpi=200, bbox_inches="tight")
    print(f"wrote {args.output.resolve()} ({len(axes.lines)} line segments)")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
