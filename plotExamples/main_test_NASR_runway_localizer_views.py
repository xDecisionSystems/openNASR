"""Render top and side views for one runway, localizer, and glide slope.

Run from the repository root after installing the plotting extra:

    python plotExamples/main_test_NASR_runway_localizer_views.py \\
        --airport ATL --runway-end 08L
"""

from __future__ import annotations

import argparse
from math import cos, radians, sin, tan
from pathlib import Path

from openNASR.cfcn import ll2xy


ILS_APPROACH_LENGTH_NM = 20.0
LOCALIZER_FULL_SCALE_WIDTH_FT = 700.0
FEET_PER_NAUTICAL_MILE = 6076.12


def _airport_center(nasr, airport_id: str) -> tuple[float, float]:
    rows = nasr["APT_BASE"]
    rows = rows[rows["ARPT_ID"].str.strip().str.upper() == airport_id]
    if len(rows) != 1:
        raise ValueError(f"Expected one FAA airport record for {airport_id!r}")
    return float(rows.iloc[0]["LAT_DECIMAL"]), float(rows.iloc[0]["LONG_DECIMAL"])


def _true_bearing(row) -> float:
    magnetic_variation = float(row["MAG_VAR"] or 0)
    if str(row["MAG_VAR_HEMIS"]).strip().upper() == "W":
        magnetic_variation = -magnetic_variation
    return (float(row["APCH_BEAR"]) + magnetic_variation) % 360


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot top and side views of a runway, localizer, and glide slope."
    )
    parser.add_argument("--airport", default="ATL", help="FAA airport identifier")
    parser.add_argument("--runway-end", default="08L", help="Runway-end identifier")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "plots" / "runway_localizer_views.png",
        help="PNG path to write (default: %(default)s)",
    )
    parser.add_argument("--show", action="store_true", help="Open the plot window")
    args = parser.parse_args()
    airport_id, runway_end_id = (
        args.airport.strip().upper(),
        args.runway_end.strip().upper(),
    )

    import matplotlib

    if not args.show:
        matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    from openNASR import NASR

    nasr = NASR()
    center = _airport_center(nasr, airport_id)
    runway_ends = nasr["APT_RWY_END"]
    runway_ends = runway_ends[
        runway_ends["ARPT_ID"].str.strip().str.upper() == airport_id
    ]
    selected_end = runway_ends[
        runway_ends["RWY_END_ID"].str.strip().str.upper() == runway_end_id
    ]
    if len(selected_end) != 1:
        raise ValueError(f"Expected one runway end {runway_end_id!r} at {airport_id}")
    runway_id = selected_end.iloc[0]["RWY_ID"]
    runway = runway_ends[runway_ends["RWY_ID"] == runway_id]
    if len(runway) != 2:
        raise ValueError(f"Expected two endpoints for runway {runway_id!r}")
    localizer = nasr["ILS_BASE"]
    localizer = localizer[
        (localizer["ARPT_ID"].str.strip().str.upper() == airport_id)
        & (localizer["RWY_END_ID"].str.strip().str.upper() == runway_end_id)
    ]
    if len(localizer) != 1:
        raise ValueError(
            f"Expected one ILS localizer for {airport_id} runway end {runway_end_id}"
        )
    glide_slope = nasr["ILS_GS"]
    glide_slope = glide_slope[
        (glide_slope["ARPT_ID"].str.strip().str.upper() == airport_id)
        & (glide_slope["RWY_END_ID"].str.strip().str.upper() == runway_end_id)
        & (
            glide_slope["ILS_LOC_ID"].str.strip().str.upper()
            == localizer.iloc[0]["ILS_LOC_ID"].strip().upper()
        )
    ]
    if len(glide_slope) != 1:
        raise ValueError(
            f"Expected one glide-slope component for {airport_id} runway end "
            f"{runway_end_id}"
        )

    threshold = selected_end.iloc[0]
    ils = localizer.iloc[0]
    glide_slope = glide_slope.iloc[0]
    threshold_x, threshold_y, _, _ = ll2xy(
        float(threshold["LAT_DECIMAL"]), float(threshold["LONG_DECIMAL"]), llc=center
    )
    localizer_x, localizer_y, _, _ = ll2xy(
        float(ils["LAT_DECIMAL"]), float(ils["LONG_DECIMAL"]), llc=center
    )
    outbound = radians((_true_bearing(ils) + 180) % 360)
    direction_x, direction_y = sin(outbound), cos(outbound)
    threshold_distance = (threshold_x - localizer_x) * direction_x + (
        threshold_y - localizer_y
    ) * direction_y
    if threshold_distance <= 0:
        raise ValueError(
            "Localizer does not lie beyond its associated runway threshold"
        )
    end_x = localizer_x + ILS_APPROACH_LENGTH_NM * direction_x
    end_y = localizer_y + ILS_APPROACH_LENGTH_NM * direction_y
    half_width_at_end = (
        LOCALIZER_FULL_SCALE_WIDTH_FT
        / 2
        / FEET_PER_NAUTICAL_MILE
        * ILS_APPROACH_LENGTH_NM
        / threshold_distance
    )
    perpendicular_x, perpendicular_y = direction_y, -direction_x
    wedge_x = (
        localizer_x,
        end_x + perpendicular_x * half_width_at_end,
        end_x - perpendicular_x * half_width_at_end,
    )
    wedge_y = (
        localizer_y,
        end_y + perpendicular_y * half_width_at_end,
        end_y - perpendicular_y * half_width_at_end,
    )

    figure, (top, side) = plt.subplots(1, 2, figsize=(14, 6))
    runway_x, runway_y, _, _ = ll2xy(
        runway["LAT_DECIMAL"].astype(float),
        runway["LONG_DECIMAL"].astype(float),
        llc=center,
    )
    top.plot(
        runway_x, runway_y, color="black", linewidth=4, label=f"Runway {runway_id}"
    )
    top.fill(
        wedge_x,
        wedge_y,
        color="tab:blue",
        alpha=0.1,
        label="ILS localizer wedge (700 ft at threshold)",
    )
    top.plot((localizer_x, end_x), (localizer_y, end_y), color="tab:blue", linewidth=1)
    top.plot(
        localizer_x,
        localizer_y,
        marker="o",
        color="tab:blue",
        linestyle="None",
        label="Localizer",
    )
    top.set_title(f"{airport_id} {runway_end_id}: top view")
    top.set_xlabel("East (NM)")
    top.set_ylabel("North (NM)")
    top.set_aspect("equal", adjustable="datalim")
    top.legend()

    threshold_elevation = float(threshold["RWY_END_ELEV"])
    localizer_elevation = float(ils["SITE_ELEVATION"])
    glide_slope_x, glide_slope_y, _, _ = ll2xy(
        float(glide_slope["LAT_DECIMAL"]),
        float(glide_slope["LONG_DECIMAL"]),
        llc=center,
    )
    glide_slope_distance = (glide_slope_x - threshold_x) * direction_x + (
        glide_slope_y - threshold_y
    ) * direction_y
    glide_slope_elevation = float(glide_slope["SITE_ELEVATION"])
    glide_slope_angle = float(glide_slope["G_S_ANGLE"])
    other_end = runway[
        runway["RWY_END_ID"].str.strip().str.upper() != runway_end_id
    ].iloc[0]
    other_x, other_y, _, _ = ll2xy(
        float(other_end["LAT_DECIMAL"]), float(other_end["LONG_DECIMAL"]), llc=center
    )
    runway_length = ((other_x - threshold_x) ** 2 + (other_y - threshold_y) ** 2) ** 0.5
    side.plot(
        (-runway_length, 0),
        (float(other_end["RWY_END_ELEV"]), threshold_elevation),
        color="black",
        linewidth=4,
        label=f"Runway {runway_id}",
    )
    approach_end_distance = ILS_APPROACH_LENGTH_NM - threshold_distance
    glide_slope_end_elevation = glide_slope_elevation + (
        approach_end_distance - glide_slope_distance
    ) * FEET_PER_NAUTICAL_MILE * tan(radians(glide_slope_angle))
    side.plot(
        (glide_slope_distance, approach_end_distance),
        (glide_slope_elevation, glide_slope_end_elevation),
        color="tab:red",
        linewidth=2,
        label=f"Glide slope ({glide_slope_angle:g}°)",
    )
    side.scatter(-threshold_distance, localizer_elevation, color="tab:blue", zorder=3)
    side.scatter(glide_slope_distance, glide_slope_elevation, color="tab:red", zorder=3)
    side.axvline(0, color="gray", linestyle="--", linewidth=1)
    side.annotate(
        "Threshold", (0, threshold_elevation), xytext=(4, 6), textcoords="offset points"
    )
    side.annotate(
        "Localizer",
        (-threshold_distance, localizer_elevation),
        xytext=(4, 6),
        textcoords="offset points",
    )
    side.annotate(
        "Glide slope",
        (glide_slope_distance, glide_slope_elevation),
        xytext=(4, 6),
        textcoords="offset points",
    )
    side.set_title(f"{airport_id} {runway_end_id}: side view")
    side.set_xlabel("NM from runway threshold (positive = approach side)")
    side.set_ylabel("Elevation (ft MSL)")
    side.legend()

    figure.tight_layout()
    figure.savefig(args.output, dpi=200, bbox_inches="tight")
    print(f"wrote {args.output.resolve()}")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
