"""Plot an ARTCC boundary with airports and high/low airways.

Run from the repository root after downloading a NASR cycle::

    python examples/plot_artcc.py
"""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt

from openNASR import NASR, PlottingIndex


# Configuration: edit these values before running the script.
artcc_id = "ZOB"
boundary_level = "high"
cycle = "2026-05-14"
cache_dir: Path | None = None
output_path = Path(__file__).with_suffix(".png")
show_plot = False

if not show_plot:
    plt.switch_backend("Agg")

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
artcc = nasr.artccs.get(artcc_id)
figure, axes = artcc.plot(
    nasr,
    level=boundary_level,
    project_to_nm=True,
    plot_fixes=False,
    plot_airnavs=False,
    index=PlottingIndex(nasr),
)
figure.set_size_inches(11, 8)
axes.set_title(f"{artcc_id}: {boundary_level}-altitude ARTCC boundary and airways")
figure.tight_layout()
output_path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(output_path, dpi=180, bbox_inches="tight")
print(f"Wrote {output_path.resolve()}")
if show_plot:
    plt.show()
else:
    plt.close(figure)
