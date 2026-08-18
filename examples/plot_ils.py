"""Plot top and side views of one runway's ILS and glide slope.

Run from the repository root after downloading a NASR cycle::

    python examples/plot_ils.py
"""

from __future__ import annotations

from math import cos, radians, sin, tan
from pathlib import Path

from matplotlib import pyplot as plt

from openNASR import NASR, plot_ils_localizer
from openNASR.coordinates import ll2xy


FEET_PER_NAUTICAL_MILE = 6076.12
APPROACH_LENGTH_NM = 15.0

# Configuration: edit these values before running the script.
airport_id = "ATL"
runway_end_id = "08L"
cycle = "2026-05-14"
cache_dir: Path | None = None
plot_wedge = True
wedge_distance_nm = 20.0
output_path = Path(__file__).with_suffix(".png")
show_plot = False


def _normalized(series):
    return series.astype(str).str.strip().str.upper()


def _true_bearing(localizer) -> float:
    variation = float(localizer["MAG_VAR"] or 0)
    if str(localizer["MAG_VAR_HEMIS"]).strip().upper() == "W":
        variation = -variation
    return (float(localizer["APCH_BEAR"]) + variation) % 360


if not show_plot:
    plt.switch_backend("Agg")

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
airport = nasr.airports.get(airport_id)
if airport.latitude is None or airport.longitude is None:
    raise ValueError(f"{airport_id} has no published airport coordinates")
center = airport.latitude, airport.longitude

runway_ends = nasr["APT_RWY_END"]
runway_ends = runway_ends[_normalized(runway_ends["ARPT_ID"]) == airport_id]
selected = runway_ends[_normalized(runway_ends["RWY_END_ID"]) == runway_end_id]
if len(selected) != 1:
    raise ValueError(f"Expected one {airport_id} runway end {runway_end_id}")
threshold = selected.iloc[0]
runway = runway_ends[runway_ends["RWY_ID"] == threshold["RWY_ID"]]
if len(runway) != 2:
    raise ValueError(f"Expected two ends for runway {threshold['RWY_ID']}")

localizers = nasr["ILS_BASE"]
localizers = localizers[
    (_normalized(localizers["ARPT_ID"]) == airport_id)
    & (_normalized(localizers["RWY_END_ID"]) == runway_end_id)
]
if len(localizers) != 1:
    raise ValueError(f"Expected one ILS for {airport_id} {runway_end_id}")
localizer = localizers.iloc[0]

glide_slopes = nasr["ILS_GS"]
glide_slopes = glide_slopes[
    (_normalized(glide_slopes["ARPT_ID"]) == airport_id)
    & (_normalized(glide_slopes["RWY_END_ID"]) == runway_end_id)
    & (
        _normalized(glide_slopes["ILS_LOC_ID"])
        == str(localizer["ILS_LOC_ID"]).strip().upper()
    )
]
if len(glide_slopes) != 1:
    raise ValueError(f"Expected one glide slope for {airport_id} {runway_end_id}")
glide_slope = glide_slopes.iloc[0]

runway_x, runway_y, _, _ = ll2xy(
    runway["LAT_DECIMAL"].astype(float),
    runway["LONG_DECIMAL"].astype(float),
    llc=center,
)
runway_x, runway_y = tuple(runway_x), tuple(runway_y)
threshold_x, threshold_y, _, _ = ll2xy(
    float(threshold["LAT_DECIMAL"]),
    float(threshold["LONG_DECIMAL"]),
    llc=center,
)
glide_x, glide_y, _, _ = ll2xy(
    float(glide_slope["LAT_DECIMAL"]),
    float(glide_slope["LONG_DECIMAL"]),
    llc=center,
)
outbound = radians((_true_bearing(localizer) + 180) % 360)
direction_x, direction_y = sin(outbound), cos(outbound)

figure, (top, side) = plt.subplots(1, 2, figsize=(14, 6))
plot_ils_localizer(
    nasr,
    localizer.to_dict(),
    axes=top,
    plot_wedge=plot_wedge,
    wedge_distance_nm=wedge_distance_nm,
    projection="nautical_miles",
    projection_center=center,
    plot_legend=False,
)
top.plot(runway_x, runway_y, color="black", linewidth=4, label="Runway")
top.scatter(glide_x, glide_y, color="tab:red", marker="^", label="Glide slope")
top.set_title(f"{airport_id} {runway_end_id}: top view")
top.set_xlabel("East (NM)")
top.set_ylabel("North (NM)")
top.set_aspect("equal", adjustable="datalim")
top.legend()

other_end = runway[_normalized(runway["RWY_END_ID"]) != runway_end_id].iloc[0]
runway_length = (
    (runway_x[1] - runway_x[0]) ** 2 + (runway_y[1] - runway_y[0]) ** 2
) ** 0.5
threshold_elevation = float(threshold["RWY_END_ELEV"])
glide_elevation = float(glide_slope["SITE_ELEVATION"])
glide_angle = float(glide_slope["G_S_ANGLE"])
glide_distance = (glide_x - threshold_x) * direction_x + (
    glide_y - threshold_y
) * direction_y
approach_elevation = glide_elevation + (
    APPROACH_LENGTH_NM - glide_distance
) * FEET_PER_NAUTICAL_MILE * tan(radians(glide_angle))
side.plot(
    (-runway_length, 0),
    (float(other_end["RWY_END_ELEV"]), threshold_elevation),
    color="black",
    linewidth=4,
    label="Runway",
)
side.plot(
    (glide_distance, APPROACH_LENGTH_NM),
    (glide_elevation, approach_elevation),
    color="tab:red",
    linewidth=2,
    label=f"{glide_angle:g}° glide slope",
)
side.scatter(glide_distance, glide_elevation, color="tab:red", zorder=3)
side.axvline(0, color="gray", linestyle="--", linewidth=1)
side.set_title(f"{airport_id} {runway_end_id}: side view")
side.set_xlabel("NM from runway threshold")
side.set_ylabel("Elevation (ft MSL)")
side.legend()

figure.tight_layout()
output_path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(output_path, dpi=180, bbox_inches="tight")
print(f"Wrote {output_path.resolve()}")
if show_plot:
    plt.show()
else:
    plt.close(figure)
