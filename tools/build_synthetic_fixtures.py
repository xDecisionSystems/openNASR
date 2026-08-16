#!/usr/bin/env python3
"""Build header-only and synthetic NASR fixtures from checked-in manifests."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "tests" / "fixtures" / "manifests"
FIXTURE_DIR = ROOT / "tests" / "fixtures"
CORE_CYCLE_STEM = "28DaySubscription_Effective_2099-01-01"


def read_manifest(schema_id: str) -> dict[str, Any]:
    return json.loads((MANIFEST_DIR / f"{schema_id}.json").read_text())


def fixture_csv_dir(category: str, schema_id: str) -> Path:
    path = FIXTURE_DIR / category / schema_id / "CSV_Data" / schema_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="raise")
        writer.writeheader()
        for values in rows:
            row = {name: "" for name in header}
            row.update(values)
            writer.writerow(row)


def build_schema_only(schema_id: str) -> None:
    manifest = read_manifest(schema_id)
    destination = fixture_csv_dir("schema_only", schema_id)
    schema_rows: dict[str, list[dict[str, object]]] = {
        filename: [] for filename in manifest["schema_description_files"]
    }
    for table_name, table in manifest["tables"].items():
        for column in table["columns"]:
            schema_rows[table["schema_description_file"]].append(
                {
                    "CSV File": table_name,
                    "Column Name": column["name"],
                    "Max Length": column["max_length"] or "",
                    "Data Type": column["faa_type"],
                    "Nullable": "Yes" if column["nullable"] else "No",
                }
            )
    for entry in manifest["csv_files"]:
        filename = entry["name"]
        if entry["kind"] == "schema_description":
            header = manifest["schema_description_header"]
            rows = schema_rows[filename]
        else:
            table_name = Path(filename).stem
            header = [
                column["name"]
                for column in manifest["tables"][table_name]["columns"]
            ]
            rows = []
        write_csv(destination / filename, header, rows)


def build_core_fixture() -> None:
    schema_id = "pre_2026_09"
    manifest = read_manifest(schema_id)
    destinations = (
        fixture_csv_dir("core", schema_id),
        FIXTURE_DIR / "cycle" / "CSV_Data" / CORE_CYCLE_STEM,
    )
    for destination in destinations:
        destination.mkdir(parents=True, exist_ok=True)
    rows = {
        "APT_BASE": [
            {
                "ARPT_ID": "BWI",
                "ICAO_ID": "KBWI",
                "LAT_DECIMAL": "39.1754",
                "LONG_DECIMAL": "-76.6684",
                "ELEV": "146",
            },
            {
                "ARPT_ID": "DCA",
                "ICAO_ID": "KDCA",
                "LAT_DECIMAL": "38.8512",
                "LONG_DECIMAL": "-77.0402",
                "ELEV": "15",
            },
        ],
        "APT_RWY": [
            {
                "ARPT_ID": "BWI",
                "RWY_ID": "10/28",
                "RWY_LEN": "5000",
                "RWY_WIDTH": "150",
                "SITE_TYPE_CODE": "A",
            },
            {
                "ARPT_ID": "DCA",
                "RWY_ID": "01/19",
                "RWY_LEN": "4000",
                "RWY_WIDTH": "100",
                "SITE_TYPE_CODE": "A",
            },
        ],
        "APT_RWY_END": [
            {
                "ARPT_ID": "BWI",
                "RWY_ID": "10/28",
                "RWY_END_ID": "10",
                "LAT_DECIMAL": "39.1750",
                "LONG_DECIMAL": "-76.6750",
                "TRUE_ALIGNMENT": "100",
            },
            {
                "ARPT_ID": "BWI",
                "RWY_ID": "10/28",
                "RWY_END_ID": "28",
                "LAT_DECIMAL": "39.1760",
                "LONG_DECIMAL": "-76.6600",
                "TRUE_ALIGNMENT": "280",
            },
            {
                "ARPT_ID": "DCA",
                "RWY_ID": "01/19",
                "RWY_END_ID": "01",
                "LAT_DECIMAL": "38.8500",
                "LONG_DECIMAL": "-77.0420",
                "TRUE_ALIGNMENT": "10",
            },
            {
                "ARPT_ID": "DCA",
                "RWY_ID": "01/19",
                "RWY_END_ID": "19",
                "LAT_DECIMAL": "38.8520",
                "LONG_DECIMAL": "-77.0380",
                "TRUE_ALIGNMENT": "190",
            },
        ],
        "ILS_BASE": [
            {
                "ARPT_ID": "BWI",
                "RWY_END_ID": "10",
                "LAT_DECIMAL": "39.1750",
                "LONG_DECIMAL": "-76.6750",
                "APCH_BEAR": "100",
                "MAG_VAR": "0",
                "MAG_VAR_HEMIS": "E",
            }
        ],
        "ILS_DME": [
            {
                "ARPT_ID": "BWI",
                "RWY_END_ID": "10",
                "LAT_DECIMAL": "39.1740",
                "LONG_DECIMAL": "-76.6740",
            }
        ],
        "ILS_GS": [
            {
                "ARPT_ID": "BWI",
                "RWY_END_ID": "10",
                "LAT_DECIMAL": "39.1730",
                "LONG_DECIMAL": "-76.6730",
                "G_S_ANGLE": "3.0",
            }
        ],
        "ILS_MKR": [
            {
                "ARPT_ID": "BWI",
                "RWY_END_ID": "10",
                "LAT_DECIMAL": "39.1720",
                "LONG_DECIMAL": "-76.6720",
            }
        ],
        "FIX_BASE": [
            {
                "FIX_ID": "AABEE",
                "LAT_DECIMAL": "39.0000",
                "LONG_DECIMAL": "-76.0000",
            }
        ],
        "NAV_BASE": [
            {
                "NAV_ID": "UNIQ",
                "NAV_TYPE": "VOR",
                "STATE_CODE": "MD",
                "COUNTRY_NAME": "UNITED STATES",
                "HIGH_ALT_ARTCC_ID": "ZDC",
                "LOW_ALT_ARTCC_ID": "ZDC",
                "LAT_DECIMAL": "39.1000",
                "LONG_DECIMAL": "-76.1000",
            },
            {
                "NAV_ID": "DUP",
                "NAV_TYPE": "VOR",
                "STATE_CODE": "IN",
                "COUNTRY_NAME": "UNITED STATES",
                "HIGH_ALT_ARTCC_ID": "ZID",
                "LOW_ALT_ARTCC_ID": "ZID",
                "LAT_DECIMAL": "40.0000",
                "LONG_DECIMAL": "-86.0000",
            },
            {
                "NAV_ID": "DUP",
                "NAV_TYPE": "NDB",
                "STATE_CODE": "OH",
                "COUNTRY_NAME": "UNITED STATES",
                "HIGH_ALT_ARTCC_ID": "ZOB",
                "LOW_ALT_ARTCC_ID": "ZOB",
                "LAT_DECIMAL": "41.0000",
                "LONG_DECIMAL": "-82.0000",
            },
        ],
        "ARB_BASE": [
            {
                "LOCATION_ID": "ZOB",
                "LOCATION_NAME": "Synthetic Cleveland ARTCC",
                "LOCATION_TYPE": "ARTCC",
                "CITY": "Cleveland",
                "STATE": "OH",
                "COUNTRY_CODE": "US",
                "LAT_DECIMAL": "41.0000",
                "LONG_DECIMAL": "-82.0000",
            }
        ],
        "ARB_SEG": [
            *(
                {
                    "LOCATION_ID": "ZOB",
                    "ALTITUDE": "HIGH",
                    "TYPE": "ARTCC",
                    "LAT_DECIMAL": latitude,
                    "LONG_DECIMAL": longitude,
                }
                for longitude, latitude in [
                    ("-82.2", "40.8"),
                    ("-81.8", "40.8"),
                    ("-81.8", "41.2"),
                    ("-82.2", "41.2"),
                    ("-82.2", "40.8"),
                ]
            ),
            *(
                {
                    "LOCATION_ID": "ZOB",
                    "ALTITUDE": "LOW",
                    "TYPE": "ARTCC",
                    "LAT_DECIMAL": latitude,
                    "LONG_DECIMAL": longitude,
                }
                for longitude, latitude in [
                    ("-82.1", "40.9"),
                    ("-81.9", "40.9"),
                    ("-81.9", "41.1"),
                    ("-82.1", "41.1"),
                    ("-82.1", "40.9"),
                ]
            ),
        ],
    }

    for table_name, table_rows in rows.items():
        header = [
            column["name"]
            for column in manifest["tables"][table_name]["columns"]
        ]
        for destination in destinations:
            write_csv(destination / f"{table_name}.csv", header, table_rows)


def main() -> None:
    build_schema_only("pre_2026_09")
    build_schema_only("nasr_2026_09")
    build_core_fixture()


if __name__ == "__main__":
    main()
