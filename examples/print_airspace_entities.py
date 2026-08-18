"""Print airports, fixes, and airways within an ARTCC boundary.

Run from the repository root after downloading a NASR cycle::

    python examples/print_airspace_entities.py
"""

from __future__ import annotations

from pathlib import Path

from openNASR import NASR


# Configuration: edit these values before running the script.
artcc_id = "ZOB"
boundary_level = "high"
cycle = "2026-05-14"
cache_dir: Path | None = None

nasr = NASR(cycle=cycle, cache_dir=cache_dir)
artcc = nasr.artccs.get(artcc_id)

for data_type in ("airports", "airways"):
    print(f"\n{data_type.title()} in {artcc_id} {boundary_level}-altitude boundary:")
    artcc.print(nasr, data_type, level=boundary_level)
