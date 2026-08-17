"""Exact-cycle DuckDB setup shared by the runnable plotting examples."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from openNASR import CycleManager, NASR


def load_duckdb_nasr(*, cycle: str | None, cache_dir: Path | None) -> NASR:
    """Build and open one exact locally cached cycle through DuckDB.

    ``cycle=None`` selects the newest *local* cycle once, then uses that exact
    date throughout.  The helper never downloads data or falls back to a
    neighboring cycle.
    """

    manager = CycleManager(cache_dir)
    effective_date = (
        manager.latest().effective_date if cycle is None else date.fromisoformat(cycle)
    )
    manager.build_duckdb(effective_date)
    return NASR(
        cycle=effective_date.isoformat(),
        cache_dir=manager.cache_dir,
        storage="duckdb",
    )
