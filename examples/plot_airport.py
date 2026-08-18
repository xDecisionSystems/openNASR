"""Plot an airport's runways, ILS sites, arrivals, and departures.

Run from the repository root after downloading a NASR cycle::

    python examples/plot_airport.py
"""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt

from openNASR import NASR, PlottingIndex, plot_airport_procedures


# Configuration: edit these values before running the script.
airport_id = "ATL"
cycle = "2026-05-14"
cache_dir: Path | None = None
ils_wedge_distance_nm = 1.0
output_path = Path(__file__).with_suffix(".png")
show_plot = False

if not show_plot:
    plt.switch_backend("Agg")

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
airport = nasr.airports.get(airport_id)
if airport.latitude is None or airport.longitude is None:
    raise ValueError(f"{airport_id} has no published airport coordinates")

center = airport.latitude, airport.longitude
index = PlottingIndex(nasr)
figure, ((runway_axes, ils_axes), (departure_axes, arrival_axes)) = plt.subplots(
    2, 2, figsize=(15, 12)
)
common = {
    "project_to_nm": True,
    "plot_legend": False,
    "index": index,
}
plot_airport_procedures(
    nasr,
    airport,
    axes=runway_axes,
    plot_departures=False,
    plot_arrivals=False,
    **common,
)
plot_airport_procedures(
    nasr,
    airport,
    axes=ils_axes,
    plot_departures=False,
    plot_arrivals=False,
    **common,
)
plot_airport_procedures(
    nasr,
    airport,
    axes=departure_axes,
    plot_runways=False,
    plot_arrivals=False,
    **common,
)
plot_airport_procedures(
    nasr,
    airport,
    axes=arrival_axes,
    plot_runways=False,
    plot_departures=False,
    **common,
)

# Draw each localizer's surveyed transmitter and the first nautical mile of
# its standard 700-foot/2.5-degree approach-course wedge.
for localizer in airport.ils:
    localizer.plot(
        nasr,
        axes=ils_axes,
        plot_wedge=True,
        wedge_distance_nm=ils_wedge_distance_nm,
        projection="nautical_miles",
        projection_center=center,
        plot_legend=False,
        index=index,
    )

runway_axes.set_title("Runways")
ils_axes.set_title("Runways and ILS component sites")
departure_axes.set_title("Departure procedures")
arrival_axes.set_title("Arrival procedures")
for axes in (runway_axes, ils_axes, departure_axes, arrival_axes):
    handles, labels = axes.get_legend_handles_labels()
    if handles:
        unique = dict(zip(labels, handles))
        axes.legend(unique.values(), unique.keys(), loc="best")
figure.suptitle(f"{airport_id} airport", fontsize=16)
figure.tight_layout()
output_path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(output_path, dpi=180, bbox_inches="tight")
print(f"Wrote {output_path.resolve()}")
if show_plot:
    plt.show()
else:
    plt.close(figure)
