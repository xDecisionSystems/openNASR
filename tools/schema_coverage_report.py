#!/usr/bin/env python3
"""Produce a machine-readable report for supported-schema CSV coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openNASR.registry import TableRegistry
from openNASR.records import FaaRecord
from openNASR.schemas import SCHEMA_SUFFIX, SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "tests" / "fixtures" / "manifests"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "schema_only"


def build_report(
    *,
    manifest_dir: str | Path = MANIFEST_DIR,
    fixture_dir: str | Path = FIXTURE_DIR,
) -> dict[str, Any]:
    """Return coverage counts and unmatched CSV names for both schemas."""

    catalog = SchemaCatalog(manifest_dir)
    registry = TableRegistry(catalog=catalog)
    reports: dict[str, Any] = {}
    for schema_id in catalog.SUPPORTED_SCHEMA_IDS:
        csv_root = Path(fixture_dir) / schema_id
        files = sorted(csv_root.rglob("*.csv"))
        operational_files = [
            path for path in files if not path.stem.endswith(SCHEMA_SUFFIX)
        ]
        schema_files = [path for path in files if path.stem.endswith(SCHEMA_SUFFIX)]
        matched = sorted(
            path.name
            for path in operational_files
            if path.stem.upper() in registry.supported_tables()
        )
        rich_record_tables = sorted(
            table_name
            for table_name in registry.supported_tables()
            if registry.table(table_name).record_type is not FaaRecord
        )
        unmatched = sorted(
            path.name
            for path in files
            if path not in operational_files
            or path.stem.upper() not in registry.supported_tables()
        )
        reports[schema_id] = {
            "total_csv_files": len(files),
            "operational_csv_files": len(operational_files),
            "schema_description_files": len(schema_files),
            "matched_table_spec_count": len(matched),
            "matched_table_spec_files": matched,
            "rich_record_table_count": len(rich_record_tables),
            "rich_record_tables": rich_record_tables,
            "unmatched_files": unmatched,
            "unmodeled_operational_files": [
                name for name in unmatched if not name.endswith(f"{SCHEMA_SUFFIX}.csv")
            ],
        }
    return {
        "manifest_directory": str(Path(manifest_dir)),
        "fixture_directory": str(Path(fixture_dir)),
        "schemas": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this scratch path instead of stdout.",
    )
    args = parser.parse_args()
    document = json.dumps(
        build_report(manifest_dir=args.manifest_dir, fixture_dir=args.fixture_dir),
        indent=2,
        sort_keys=True,
    )
    if args.output is None:
        print(document)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
