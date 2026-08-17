#!/usr/bin/env python3
"""Add collapsible raw-field catalogs to the major domain-type pages.

The generator uses ``RICH_RECORD_TYPES`` as the authoritative record-to-table
mapping and the checked-in CSV reference pages as the field-description source.
Run it after ``generate_csv_reference.py`` whenever the FAA schema changes.
"""

from __future__ import annotations

import re
from pathlib import Path

from openNASR.registry import RICH_RECORD_TYPES


BEGIN = "<!-- BEGIN GENERATED RECORD FIELDS -->"
END = "<!-- END GENERATED RECORD FIELDS -->"
AUTCLASS = re.compile(r"\.\. autoclass:: ([\w.]+)")


def _slug(table: str) -> str:
    return table.lower().replace("_", "-")


def _field_rows(csv_page: Path) -> list[tuple[str, str]]:
    rows = []
    for line in csv_page.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = line[1:-1].split(" | ")
        if len(cells) != 6:
            raise ValueError(f"Unexpected CSV reference row in {csv_page}: {line}")
        rows.append((cells[0].strip(), cells[1].strip()))
    if not rows:
        raise ValueError(f"No field rows found in {csv_page}")
    return rows


def _record_map() -> dict[str, str]:
    return {
        f"{record_type.__module__}.{record_type.__name__}": table
        for table, record_type in RICH_RECORD_TYPES.items()
    }


def _dropdown(qualified_name: str, table: str, csv_dir: Path) -> list[str]:
    class_name = qualified_name.rsplit(".", 1)[-1]
    slug = _slug(table)
    rows = _field_rows(csv_dir / f"{slug}.md")
    return [
        f"```{{faa-dropdown}} {class_name} raw fields — {table} ({len(rows)})",
        f"`{class_name}` preserves one complete `{table}` row. These fields are",
        "available by mapping key or attribute name, even when the class does not",
        "declare a dedicated typed property for each one.",
        "",
        "| Field | Description |",
        "| --- | --- |",
        *(f"| {field} | {description} |" for field, description in rows),
        "",
        f"[Complete `{table}` column reference](../csv-tables/{slug}.md)",
        "```",
        "",
    ]


def generate(types_dir: Path, csv_dir: Path) -> tuple[int, int]:
    record_map = _record_map()
    pages_changed = 0
    dropdowns_written = 0
    for page in sorted(types_dir.glob("*.md")):
        source = page.read_text(encoding="utf-8")
        qualified_names = [
            name for name in AUTCLASS.findall(source) if name in record_map
        ]
        if not qualified_names:
            continue
        lines = [
            BEGIN,
            "",
            "## Record fields",
            "",
            "Expand a record below to see every lossless FAA field it contains.",
            "The generated Python API follows this source-field catalog.",
            "",
        ]
        for qualified_name in qualified_names:
            lines.extend(_dropdown(qualified_name, record_map[qualified_name], csv_dir))
        lines.append(END)
        block = "\n".join(lines)
        if BEGIN in source:
            prefix, remainder = source.split(BEGIN, 1)
            _old, suffix = remainder.split(END, 1)
            updated = prefix + block + suffix
        else:
            marker = "## Generated API"
            updated = (
                source.replace(marker, f"{block}\n\n{marker}", 1)
                if marker in source
                else source.rstrip() + f"\n\n{block}\n"
            )
        if updated != source:
            page.write_text(updated, encoding="utf-8")
            pages_changed += 1
        dropdowns_written += len(qualified_names)
    return pages_changed, dropdowns_written


def main() -> None:
    docs_dir = Path(__file__).resolve().parents[1]
    changed, dropdowns = generate(docs_dir / "types", docs_dir / "csv-tables")
    print(f"Generated {dropdowns} record dropdowns; changed {changed} pages")


if __name__ == "__main__":
    main()
