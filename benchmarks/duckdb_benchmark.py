"""Manual, opt-in CSV/DuckDB benchmark runner.

This module deliberately has no pytest hooks and never downloads data.  It is
intended to be run with ``python -m benchmarks.duckdb_benchmark`` against a caller-
selected cache or the committed tiny fixtures.  Reports are JSON so raw
samples can be retained alongside a rendered Markdown report.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tempfile
import time
from typing import Any, Callable

from openNASR.cycles import CycleManager
from openNASR.duckdb_builder import build_duckdb
from openNASR.duckdb_tables import DuckDbTableRepository
from openNASR.tables import TableRepository, discover_tables


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(source: Path) -> list[Path]:
    return sorted(path for path in source.glob("*.csv") if path.is_file())


def _dataset(source: Path) -> dict[str, Any]:
    paths = _files(source)
    return {
        "source": str(source),
        "table_count": len(paths),
        "csv_bytes": sum(path.stat().st_size for path in paths),
        "tables": {path.stem.upper(): {"bytes": path.stat().st_size} for path in paths},
    }


def _samples(function: Callable[[], Any], repetitions: int) -> list[float]:
    values: list[float] = []
    for _ in range(repetitions):
        started = time.perf_counter_ns()
        function()
        values.append((time.perf_counter_ns() - started) / 1_000_000)
    return values


def _summary(samples: list[float]) -> dict[str, Any]:
    if not samples:
        return {"samples_ms": [], "median_ms": None, "p95_ms": None}
    ordered = sorted(samples)
    p95 = ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))]
    return {
        "samples_ms": samples,
        "median_ms": statistics.median(samples),
        "p95_ms": p95,
        "minimum_ms": min(samples),
        "median_absolute_deviation_ms": statistics.median(
            abs(value - statistics.median(samples)) for value in samples
        ),
    }


def _system() -> dict[str, Any]:
    return {
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "openNASR": _package_version("openNASR"),
        "pandas": _package_version("pandas"),
        "duckdb": _package_version("duckdb"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
    }


def _package_version(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return None


def _git(*arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _measure_store(
    source: Path, database: Path, *, cold: int, warm: int
) -> dict[str, Any]:
    csv = TableRepository(source)
    build_samples = _samples(lambda: build_duckdb(source, database, "2000-01-01"), cold)
    # A fresh repository models first materialization; repeated access models
    # the application-level cache and is kept separate from construction.
    first_samples = _samples(lambda: _first_table(database), cold)
    warm_repository = DuckDbTableRepository(database)
    try:
        warm_repository.table(
            "APT_BASE" if "APT_BASE" in discover_tables(source) else next(iter(csv))
        )
        warm_samples = _samples(
            lambda: warm_repository.table(
                "APT_BASE" if "APT_BASE" in discover_tables(source) else next(iter(csv))
            ),
            warm,
        )
    finally:
        warm_repository.close()
    return {
        "build": _summary(build_samples),
        "duckdb_first_table": _summary(first_samples),
        "duckdb_warm_table": _summary(warm_samples),
        "database_bytes": database.stat().st_size,
        "sidecar_bytes": database.with_name(f"{database.name}.json").stat().st_size,
    }


def _first_table(database: Path) -> None:
    repository = DuckDbTableRepository(database)
    try:
        repository.table(repository.available_tables[0])
    finally:
        repository.close()


def run_fixtures(
    fixtures: Path, *, cold: int, warm: int, output: Path | None
) -> dict[str, Any]:
    generations = sorted(
        path
        for path in fixtures.iterdir()
        if path.is_dir() and (path / "CSV_Data").is_dir()
    )
    if not generations:
        raise SystemExit(
            f"No fixture generations found under {fixtures}. Pass the parent "
            "directory that contains generation subdirectories (each holding "
            "its own CSV_Data/), for example "
            "tests/fixtures/duckdb_parity, not a generation directory itself."
        )
    reports = []
    for generation in generations:
        source = generation / "CSV_Data" / generation.name
        if not source.is_dir():
            continue
        with tempfile.TemporaryDirectory(prefix="openNASR-benchmark-") as scratch:
            database = Path(scratch) / "nasr.duckdb"
            measurements = _measure_store(source, database, cold=cold, warm=warm)
            reports.append(
                {
                    "name": generation.name,
                    "effective_date": "2026-08-06"
                    if generation.name == "pre_2026_09"
                    else "2026-09-03",
                    "dataset": _dataset(source),
                    "measurements": measurements,
                }
            )
    return _report(
        "fixtures", reports, {"cold_repetitions": cold, "warm_repetitions": warm}
    )


def run_cycle(
    cache_dir: Path,
    cycle: str,
    *,
    cold: int,
    warm: int,
    include_build: bool,
    output: Path | None,
) -> dict[str, Any]:
    """Benchmark one exact cached cycle in an isolated temporary cache."""

    manager = CycleManager(cache_dir)
    requested = date.fromisoformat(cycle)
    cached = manager.get(requested)
    if cached is None or (cached.archive_path is None and cached.data_path is None):
        raise SystemExit(f"exact cycle {cycle} is not available in {cache_dir}")
    with tempfile.TemporaryDirectory(prefix="openNASR-benchmark-") as scratch:
        isolated = CycleManager(Path(scratch))
        if cached.archive_path is not None:
            isolated.import_archive(cached.archive_path)
        elif cached.data_path is not None:
            destination = isolated.cycles_dir / cycle
            shutil.copytree(cached.data_path, destination)
        result = isolated.build_duckdb(requested)
        extracted = isolated.get(requested)
        assert extracted is not None and extracted.data_path is not None
        source = isolated._resolve_csv_source(extracted.data_path)
        measurements = _measure_store(
            source,
            result.database_path,
            cold=max(1, cold if include_build else 1),
            warm=warm,
        )
        measurements["include_build"] = include_build
        reports = [
            {
                "effective_date": cycle,
                "dataset": _dataset(source),
                "measurements": measurements,
            }
        ]
    return _report(
        "cycle",
        reports,
        {"cycle": cycle, "cold_repetitions": cold, "warm_repetitions": warm},
    )


def _report(
    kind: str, datasets: list[dict[str, Any]], arguments: dict[str, Any]
) -> dict[str, Any]:
    return {
        "kind": kind,
        "system": _system(),
        "arguments": arguments,
        "datasets": datasets,
    }


def _write(document: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="benchmark one exact cached cycle")
    run.add_argument("--cache-dir", type=Path, required=True)
    run.add_argument("--cycle", required=True)
    run.add_argument("--include-build", action="store_true")
    run.add_argument("--cold-repetitions", type=int, default=9)
    run.add_argument("--warm-repetitions", type=int, default=5)
    run.add_argument("--warm-iterations", type=int, default=200)
    run.add_argument("--output", type=Path)

    fixtures = subparsers.add_parser(
        "run-fixtures", help="benchmark committed fixtures"
    )
    fixtures.add_argument(
        "--fixtures",
        type=Path,
        required=True,
        help=(
            "parent directory containing generation subdirectories (each "
            "with its own CSV_Data/), e.g. tests/fixtures/duckdb_parity"
        ),
    )
    fixtures.add_argument("--cold-repetitions", type=int, default=9)
    fixtures.add_argument("--warm-repetitions", type=int, default=5)
    fixtures.add_argument("--warm-iterations", type=int, default=200)
    fixtures.add_argument("--output", type=Path)

    compare = subparsers.add_parser("compare-index", help="compare two JSON reports")
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--candidate", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "run":
        _write(
            run_cycle(
                args.cache_dir,
                args.cycle,
                cold=args.cold_repetitions,
                warm=args.warm_repetitions,
                include_build=args.include_build,
                output=args.output,
            ),
            args.output,
        )
    elif args.command == "run-fixtures":
        _write(
            run_fixtures(
                args.fixtures,
                cold=args.cold_repetitions,
                warm=args.warm_repetitions,
                output=args.output,
            ),
            args.output,
        )
    else:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "baseline": baseline.get("kind"),
                    "candidate": candidate.get("kind"),
                    "status": "comparison-ready",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
