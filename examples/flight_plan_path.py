"""Convert an FAA flight-plan route field into a latitude/longitude path.

Run from the repository root after downloading a NASR cycle::

    python examples/flight_plan_path.py
"""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

from matplotlib import pyplot as plt

from openNASR import NASR, PlottingIndex, RouteResolver, plot_flight_plan


# Configuration: edit these values before running the script.
route = "KLAX.DOTSS2.CLEEE..PKE.J74.TXO.J72.TURKI.JOVEM6.KDFW/0235"
cycle = "2026-05-14"
cache_dir: Path | None = None
output_path = Path(__file__).with_suffix(".png")
show_plot = False

if not show_plot:
    plt.switch_backend("Agg")

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
resolver = RouteResolver(nasr)
path = resolver.path(route)

print("Latitude, longitude path:")
for latitude, longitude in path:
    print(f"  {latitude:.8f}, {longitude:.8f}")

index = PlottingIndex(nasr)
figure, axes = plot_flight_plan(
    nasr,
    route,
    projection="web_mercator",
    index=index,
)
figure.set_size_inches(10, 7)
axes.set_title(f"Flight-plan path\n{fill(route, width=72)}")
figure.tight_layout()
output_path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(output_path, dpi=180, bbox_inches="tight")
print(f"Wrote {output_path.resolve()}")
if show_plot:
    plt.show()
else:
    plt.close(figure)
