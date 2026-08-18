"""Plot the Honolulu CTA/FIR boundary from the FAA ARB tables.

Run from the repository root after downloading a NASR cycle::

    python examples/plot_fir.py
"""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt

from openNASR import NASR


# Configuration: edit these values before running the script.
location_id = "ZSU"
boundary_type = "CTA/FIR"
altitude = "UNLIMITED"
cycle = "2026-05-14"
cache_dir: Path | None = None
output_path = Path(__file__).with_suffix(".png")
show_plot = False

if not show_plot:
    plt.switch_backend("Agg")

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
boundary = nasr.airspace_boundaries.get(
    location_id, boundary_type=boundary_type, altitude=altitude
)
figure, axes = boundary.plot(
    nasr,
    plot_high_airways=True,
    plot_low_airways=True,
    plot_airports=True,
    plot_fixes=True,
    plot_airnavs=True,
    projection="geographic",
    plot_legend=False,
)

minimum_longitude, minimum_latitude, maximum_longitude, maximum_latitude = (
    boundary.geometry.bounds
)
longitude_padding = (maximum_longitude - minimum_longitude) * 0.05
latitude_padding = (maximum_latitude - minimum_latitude) * 0.05
axes.set_xlim(
    minimum_longitude - longitude_padding, maximum_longitude + longitude_padding
)
axes.set_ylim(minimum_latitude - latitude_padding, maximum_latitude + latitude_padding)
axes.set_aspect("equal", adjustable="box")
axes.set_title(f"{boundary.record.name} CTA/FIR ({location_id})")
figure.tight_layout()
output_path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(output_path, dpi=180, bbox_inches="tight")
print(f"Wrote {output_path.resolve()}")
if show_plot:
    plt.show()
else:
    plt.close(figure)
