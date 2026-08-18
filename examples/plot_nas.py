"""Plot all National Airspace System ARTCC boundaries and airways.

Run from the repository root after downloading a NASR cycle::

    python examples/plot_nas.py
"""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt
from shapely import make_valid, unary_union

from openNASR import NASR, PlottingIndex, plot_airspace


# Configuration: edit these values before running the script.
cycle = "2026-05-14"
cache_dir: Path | None = None
output_path = Path(__file__).with_suffix(".png")
show_plot = False

if not show_plot:
    plt.switch_backend("Agg")

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
artcc_boundaries = [
    (artcc.location_id, make_valid(artcc.high.getShape))
    for artcc in nasr.artccs.find()
    if artcc.high is not None
]
if not artcc_boundaries:
    raise RuntimeError("The selected NASR cycle has no high-altitude ARTCC boundaries")

index = PlottingIndex(nasr)
continental_boundaries = [
    boundary for location_id, boundary in artcc_boundaries if location_id != "ZAN"
]
alaska_boundaries = [
    boundary for location_id, boundary in artcc_boundaries if location_id == "ZAN"
]
figure, (continental_axes, alaska_axes) = plt.subplots(
    1, 2, figsize=(16, 8), gridspec_kw={"width_ratios": (3, 1)}
)

plot_airspace(
    nasr,
    unary_union(continental_boundaries),
    axes=continental_axes,
    plot_airports=False,
    plot_fixes=False,
    plot_airnavs=False,
    projection="web_mercator",
    basemap="usgs_imagery",
    plot_legend=True,
    index=index,
)
for artcc_boundary in continental_boundaries:
    plot_airspace(
        nasr,
        artcc_boundary,
        axes=continental_axes,
        plot_high_airways=False,
        plot_low_airways=False,
        plot_airports=False,
        plot_fixes=False,
        plot_airnavs=False,
        plot_legend=False,
        projection="web_mercator",
        index=index,
    )
# Preserve the imagery-aligned axes box after overlaying individual boundaries.
continental_axes.set_aspect("equal", adjustable="box")

if alaska_boundaries:
    plot_airspace(
        nasr,
        unary_union(alaska_boundaries),
        axes=alaska_axes,
        plot_airports=False,
        plot_fixes=False,
        plot_airnavs=False,
        projection="geographic",
        plot_legend=False,
        index=index,
    )
    for artcc_boundary in alaska_boundaries:
        plot_airspace(
            nasr,
            artcc_boundary,
            axes=alaska_axes,
            plot_high_airways=False,
            plot_low_airways=False,
            plot_airports=False,
            plot_fixes=False,
            plot_airnavs=False,
            plot_legend=False,
            projection="geographic",
            index=index,
        )
    # ZAN's published oceanic boundary continues across the antimeridian to
    # the North Pole. Focus the inset on the operational Alaska region while
    # the complete geometry remains available in the source data.
    alaska_axes.set_xlim(-180, -120)
    alaska_axes.set_ylim(45, 75)
    alaska_axes.set_aspect("equal", adjustable="box")
    alaska_axes.set_title("Alaska Center (ZAN)")

continental_axes.set_title("Continental U.S. ARTCC boundaries and airways")
figure.suptitle("National Airspace System", fontsize=18)
figure.tight_layout()
output_path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(output_path, dpi=180, bbox_inches="tight")
print(f"Wrote {output_path.resolve()}")
if show_plot:
    plt.show()
else:
    plt.close(figure)
