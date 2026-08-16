from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST_DIR = ROOT / "tests" / "fixtures" / "manifests"
FILESTYPES = ROOT / "FILESTYPES.md"


def _manifest(schema_id: str) -> dict:
    return json.loads((MANIFEST_DIR / f"{schema_id}.json").read_text())


def _approved_tables() -> set[str]:
    return set(
        re.findall(r"^\| `([A-Z][A-Z0-9_ ]*)` \|", FILESTYPES.read_text(), re.MULTILINE)
    )


def test_manifest_inventory_matches_approved_table_names():
    manifests = [_manifest("pre_2026_09"), _manifest("nasr_2026_09")]
    manifest_tables = set().union(*(set(manifest["tables"]) for manifest in manifests))

    assert _approved_tables() == manifest_tables


def test_all_manifest_files_have_an_explicit_inventory_entry():
    for schema_id in ("pre_2026_09", "nasr_2026_09"):
        manifest = _manifest(schema_id)
        files = {entry["name"] for entry in manifest["csv_files"]}
        expected_operational = {f"{table}.csv" for table in manifest["tables"]}
        expected_schema = set(manifest["schema_description_files"])

        assert files == expected_operational | expected_schema
        assert len(files) == manifest["inventory"]["csv_file_count"]
