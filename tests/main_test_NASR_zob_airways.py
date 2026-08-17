"""Render ZOB with high- and low-altitude FAA airways.

Run from the repository root after installing the plotting extra:

    python tests/main_test_NASR_zob_airways.py
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot ZOB with high- and low-altitude airways."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("zob_high_low_airways.png"),
        help="PNG path to write (default: %(default)s)",
    )
    parser.add_argument("--show", action="store_true", help="Open the plot window")
    args = parser.parse_args()

    import matplotlib

    if not args.show:
        matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from shapely.ops import unary_union

    from openNASR import NASR, plot_airspace

    nasr = NASR()
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
    )
    axes.set_title("ZOB: high- and low-altitude airways")
    figure.savefig(args.output, dpi=200, bbox_inches="tight")
    print(f"wrote {args.output.resolve()} ({len(axes.lines)} line segments)")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
