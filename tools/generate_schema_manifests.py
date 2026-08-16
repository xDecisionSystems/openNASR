#!/usr/bin/env python3
"""Generate deterministic FAA NASR schema manifests from official CSV ZIPs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from zipfile import ZipFile


SCHEMA_SUFFIX = "_CSV_DATA_STRUCTURE.csv"
SCHEMA_HEADERS = (
    "CSV File",
    "Column Name",
    "Max Length",
    "Data Type",
    "Nullable",
)

SOURCES = {
    "pre": {
        "schema_id": "pre_2026_09",
        "effective_date": "2026-08-06",
        "archive_filename": "06_Aug_2026_CSV.zip",
        "source_url": (
            "https://nfdc.faa.gov/webContent/28DaySub/extra/"
            "06_Aug_2026_CSV.zip"
        ),
        "source_page": (
            "https://www.faa.gov/air_traffic/flight_info/aeronav/"
            "Aero_Data/NASR_Subscription/2026-08-06/"
        ),
        "role": "supported subscription schema before NASR 10.1",
    },
    "post": {
        "schema_id": "nasr_2026_09",
        "effective_date": "2026-09-03",
        "archive_filename": "03_Sep_2026_CSV.zip",
        "source_url": (
            "https://nfdc.faa.gov/webContent/28DaySub/extra/"
            "03_Sep_2026_CSV.zip"
        ),
        "source_page": (
            "https://www.faa.gov/air_traffic/flight_info/aeronav/"
            "Aero_Data/NASR_Subscription/2026-09-03/"
        ),
        "role": "supported NASR 10.1 subscription schema",
    },
    "test": {
        "format_effective_date": "2026-09-03",
        "archive_filename": "NASR_10_1_TEST_CSV.zip",
        "source_url": (
            "https://nfdc.faa.gov/webContent/28DaySub/Test_Subscriber_Files/"
            "NASR_10_1_TEST_CSV.zip"
        ),
        "source_page": (
            "https://www.faa.gov/air_traffic/flight_info/aeronav/"
            "Aero_Data/NASR_Subscription/"
        ),
        "role": "FAA NASR 10.1 CSV test subscriber package",
    },
    "notice": {
        "format_effective_date": "2026-09-03",
        "archive_filename": "NASR_26-01_DPN_10.1_Subscriber_Enhancement.pdf",
        "source_url": (
            "https://www.faa.gov/air_traffic/flight_info/aeronav/"
            "safety_alerts/media/NASR_26-01_DPN_10.1_Subscriber_Enhancement.pdf"
        ),
        "source_page": (
            "https://www.faa.gov/air_traffic/flight_info/aeronav/safety_alerts/"
        ),
        "role": "FAA NASR 26-01 data product notice",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_headers(archive: ZipFile, names: Iterable[str]) -> dict[str, list[str]]:
    headers: dict[str, list[str]] = {}
    for name in names:
        with archive.open(name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            headers[Path(name).stem] = next(csv.reader(text))
    return headers


def build_manifest(path: Path, source: dict[str, str]) -> dict[str, Any]:
    tables: dict[str, dict[str, Any]] = {}
    with ZipFile(path) as archive:
        csv_names = sorted(
            name for name in archive.namelist() if name.lower().endswith(".csv")
        )
        schema_names = sorted(name for name in csv_names if name.endswith(SCHEMA_SUFFIX))
        operational_names = sorted(set(csv_names) - set(schema_names))

        for schema_name in schema_names:
            with archive.open(schema_name) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                reader = csv.DictReader(text)
                if tuple(reader.fieldnames or ()) != SCHEMA_HEADERS:
                    raise ValueError(
                        f"Unexpected schema headers in {schema_name}: {reader.fieldnames}"
                    )
                for row in reader:
                    table_name = row["CSV File"]
                    table = tables.setdefault(
                        table_name,
                        {
                            "csv_file": f"{table_name}.csv",
                            "schema_description_file": schema_name,
                            "columns": [],
                        },
                    )
                    if table["schema_description_file"] != schema_name:
                        raise ValueError(f"{table_name} described by multiple schema files")
                    nullable_text = row["Nullable"].strip().lower()
                    if nullable_text not in {"yes", "no"}:
                        raise ValueError(
                            f"Unexpected Nullable value for {table_name}: {row['Nullable']}"
                        )
                    table["columns"].append(
                        {
                            "name": row["Column Name"],
                            "faa_type": row["Data Type"],
                            "max_length": row["Max Length"] or None,
                            "nullable": nullable_text == "yes",
                        }
                    )

        operational_tables = {Path(name).stem for name in operational_names}
        described_tables = set(tables)
        if operational_tables != described_tables:
            raise ValueError(
                "FAA CSV/schema mismatch: "
                f"undescribed={sorted(operational_tables - described_tables)}, "
                f"missing_csv={sorted(described_tables - operational_tables)}"
            )

        actual_headers = csv_headers(archive, operational_names)
        for table_name, table in tables.items():
            declared = [column["name"] for column in table["columns"]]
            actual = actual_headers[table_name]
            normalized_declared = [name.strip().upper() for name in declared]
            normalized_actual = [name.strip().upper() for name in actual]
            if normalized_actual != normalized_declared:
                raise ValueError(f"Header does not match FAA schema for {table_name}")
            for actual_name, declared_name, column in zip(
                actual, declared, table["columns"], strict=True
            ):
                if actual_name != declared_name:
                    column["faa_declared_name"] = declared_name
                    column["name"] = actual_name

    ordered_tables = {name: tables[name] for name in sorted(tables)}
    return {
        "schema_id": source["schema_id"],
        "effective_date": source["effective_date"],
        "source_artifact": source["archive_filename"],
        "inventory": {
            "csv_file_count": len(operational_names) + len(schema_names),
            "operational_table_count": len(operational_names),
            "schema_description_file_count": len(schema_names),
        },
        "csv_files": [
            *(
                {"name": name, "kind": "operational"}
                for name in operational_names
            ),
            *(
                {"name": name, "kind": "schema_description"}
                for name in schema_names
            ),
        ],
        "schema_description_files": schema_names,
        "schema_description_header": list(SCHEMA_HEADERS),
        "schema_description_metadata_note": (
            "FAA schema-description CSVs are self-describing catalogs and do not "
            "declare their own types, lengths, or nullability."
        ),
        "tables": ordered_tables,
    }


def compare_manifests(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_tables = before["tables"]
    after_tables = after["tables"]
    added_tables = sorted(after_tables.keys() - before_tables.keys())
    removed_tables = sorted(before_tables.keys() - after_tables.keys())
    table_changes: dict[str, Any] = {}
    changed_column_count = 0
    added_column_count = 0
    removed_column_count = 0
    faa_type_change_count = 0
    max_length_change_count = 0
    nullability_change_count = 0

    for table_name in sorted(before_tables.keys() & after_tables.keys()):
        old_columns = before_tables[table_name]["columns"]
        new_columns = after_tables[table_name]["columns"]
        old_by_name = {column["name"]: column for column in old_columns}
        new_by_name = {column["name"]: column for column in new_columns}
        added_names = new_by_name.keys() - old_by_name.keys()
        removed_names = old_by_name.keys() - new_by_name.keys()
        changed_names = {
            name
            for name in old_by_name.keys() & new_by_name.keys()
            if old_by_name[name] != new_by_name[name]
        }
        old_order = [column["name"] for column in old_columns]
        new_order = [column["name"] for column in new_columns]
        if not (added_names or removed_names or changed_names or old_order != new_order):
            continue

        added_column_count += len(added_names)
        removed_column_count += len(removed_names)
        changed_column_count += len(changed_names)
        for name in changed_names:
            if old_by_name[name]["faa_type"] != new_by_name[name]["faa_type"]:
                faa_type_change_count += 1
            if old_by_name[name]["max_length"] != new_by_name[name]["max_length"]:
                max_length_change_count += 1
            if old_by_name[name]["nullable"] != new_by_name[name]["nullable"]:
                nullability_change_count += 1
        table_changes[table_name] = {
            "columns_added": [new_by_name[name] for name in new_order if name in added_names],
            "columns_removed": [
                old_by_name[name] for name in old_order if name in removed_names
            ],
            "columns_changed": [
                {
                    "name": name,
                    "before": old_by_name[name],
                    "after": new_by_name[name],
                }
                for name in old_order
                if name in changed_names
            ],
            "column_order_before": old_order,
            "column_order_after": new_order,
        }

    return {
        "from_schema": before["schema_id"],
        "to_schema": after["schema_id"],
        "effective_date": after["effective_date"],
        "review_status": "reviewed against FAA NASR 26-01 DPN and test headers",
        "sources": [
            before["source_artifact"],
            after["source_artifact"],
            SOURCES["test"]["archive_filename"],
            SOURCES["notice"]["archive_filename"],
        ],
        "summary": {
            "tables_added": len(added_tables),
            "tables_removed": len(removed_tables),
            "tables_changed": len(table_changes),
            "columns_added": added_column_count,
            "columns_removed": removed_column_count,
            "column_definitions_changed": changed_column_count,
            "faa_type_changes": faa_type_change_count,
            "max_length_changes": max_length_change_count,
            "nullability_changes": nullability_change_count,
            "one_to_one_column_renames": 0,
        },
        "tables_added": added_tables,
        "tables_removed": removed_tables,
        "table_changes": table_changes,
        "reviewed_replacements": [
            {
                "table": "APT_RWY",
                "removed": ["PCN"],
                "added": ["PAVEMENT_CLASSIFICATION", "PCN_PCR_NUMBER"],
                "basis": "FAA NASR 26-01 DPN, CSV Subscriber Updates section B.1",
            }
        ],
        "value_domain_changes_without_structural_schema_changes": [
            {
                "tables": ["AWY_BASE"],
                "fields": ["AWY_DESIGNATION"],
                "change": "SP special-route designation added",
                "basis": "FAA NASR 26-01 DPN, CSV Subscriber Updates section B.3",
            },
            {
                "tables": ["FIX_BASE", "FIX_CHRT"],
                "fields": ["CHARTS", "CHARTING_TYPE_DESC"],
                "change": "SPECIAL ENROUTE charting type added",
                "basis": "FAA NASR 26-01 DPN, CSV Subscriber Updates section B.2",
            },
        ],
    }


def validate_test_headers(test_path: Path, manifest: dict[str, Any]) -> None:
    with ZipFile(test_path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv") and not name.endswith(SCHEMA_SUFFIX)
        )
        headers = csv_headers(archive, names)
    declared_tables = set(manifest["tables"])
    if set(headers) != declared_tables:
        raise ValueError("Test package table inventory differs from September manifest")
    for table_name, actual in headers.items():
        declared = [column["name"] for column in manifest["tables"][table_name]["columns"]]
        if actual != declared:
            raise ValueError(f"Test package header mismatch for {table_name}")


def artifact_metadata(path: Path, source: dict[str, str]) -> dict[str, Any]:
    metadata = dict(source)
    metadata.update(
        {
            "byte_size": path.stat().st_size,
            "sha256": sha256(path),
        }
    )
    return metadata


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-zip", type=Path, required=True)
    parser.add_argument("--post-zip", type=Path, required=True)
    parser.add_argument("--test-zip", type=Path, required=True)
    parser.add_argument("--notice", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    before = build_manifest(args.pre_zip, SOURCES["pre"])
    after = build_manifest(args.post_zip, SOURCES["post"])
    validate_test_headers(args.test_zip, after)
    changes = compare_manifests(before, after)
    provenance = {
        "retrieved_on": "2026-08-16",
        "artifacts": [
            artifact_metadata(args.pre_zip, SOURCES["pre"]),
            artifact_metadata(args.post_zip, SOURCES["post"]),
            artifact_metadata(args.test_zip, SOURCES["test"]),
            artifact_metadata(args.notice, SOURCES["notice"]),
        ],
        "validation": {
            "nasr_10_1_test_headers_match_2026_09_manifest": True,
            "operational_rows_in_repository": False,
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "pre_2026_09.json", before)
    write_json(args.output_dir / "nasr_2026_09.json", after)
    write_json(args.output_dir / "2026_09_changes.json", changes)
    write_json(args.output_dir / "provenance.json", provenance)


if __name__ == "__main__":
    main()
