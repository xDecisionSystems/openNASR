"""Plot one runway and its ILS localizer.

Run from the repository root after downloading a NASR cycle::

    python examples/plot_ils.py
"""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt

from openNASR import NASR, PlottingIndex


# Configuration: edit these values before running the script.
airport_id = "ATL"
runway_id = "08L/26R"
runway_end_id = "08L"
cycle = "2026-05-14"
cache_dir: Path | None = None
plot_wedge = True
wedge_distance_nm = 20.0
output_path = Path(__file__).with_suffix(".png")
show_plot = False

if not show_plot:
    plt.switch_backend("Agg")

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
airport = nasr.airports.get(airport_id)
runway = next(
    record
    for record in airport.runways
    if str(record["RWY_ID"]).strip().upper() == runway_id
)
localizer = next(
    record
    for record in airport.ils
    if str(record["RWY_END_ID"]).strip().upper() == runway_end_id
)
if airport.latitude is None or airport.longitude is None:
    raise ValueError(f"{airport_id} has no published airport coordinates")
center = airport.latitude, airport.longitude
index = PlottingIndex(nasr)

figure, (top_axes, side_axes) = plt.subplots(1, 2, figsize=(14, 6))
runway.plot(
    nasr,
    axes=top_axes,
    projection="nautical_miles",
    projection_center=center,
    plot_legend=False,
    index=index,
)
localizer.plot(
    nasr,
    axes=top_axes,
    side_axes=side_axes,
    plot_wedge=plot_wedge,
    wedge_distance_nm=wedge_distance_nm,
    projection="nautical_miles",
    projection_center=center,
    plot_legend=False,
    index=index,
)

top_axes.set_title(f"{airport_id} runway {runway_end_id}: top view")
top_axes.legend()
side_axes.legend()
figure.tight_layout()
output_path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(output_path, dpi=180, bbox_inches="tight")
print(f"Wrote {output_path.resolve()}")
if show_plot:
    plt.show()
else:
    plt.close(figure)
