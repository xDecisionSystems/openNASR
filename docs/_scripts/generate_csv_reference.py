#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate one Sphinx/MyST reference page per FAA NASR operational CSV.

The source directory must be an extracted FAA ``*_CSV`` directory containing
the operational CSVs, ``*_CSV_DATA_STRUCTURE.csv`` files, and matching
``* DATA LAYOUT.pdf`` files. Generated pages are checked in so Read the Docs
does not need a downloaded NASR cycle or ``pdftotext``.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from collections import defaultdict
from pathlib import Path


TABLE_DESCRIPTIONS = {
    "APT_ARS": "Airport arresting systems and the runways on which they are installed.",
    "APT_ATT": "Published airport attendance schedules and attendance remarks.",
    "APT_BASE": "Core landing-facility identity, location, ownership, operational, and services information.",
    "APT_CON": "Airport owner, manager, and other published contact information.",
    "APT_RMK": "Remarks associated with an airport or a specific airport field.",
    "APT_RWY": "Airport runway identity, dimensions, surface, lighting, and operational information.",
    "APT_RWY_END": "Physical runway-end coordinates, elevations, declared distances, markings, and approach information.",
    "ARB_BASE": "Air Route Traffic Control Center identity and reference-location information.",
    "ARB_SEG": "Ordered high- and low-altitude ARTCC boundary vertices.",
    "ATC_ATIS": "Automatic Terminal Information Service records associated with an ATC facility.",
    "ATC_BASE": "Core airport traffic control facility identity, location, and operating information.",
    "ATC_RMK": "Remarks associated with an ATC facility or one of its fields.",
    "ATC_SVC": "Services published for an airport traffic control facility.",
    "AWOS": "Automated weather observing station identity, location, equipment, and commissioning information.",
    "AWY_BASE": "Airway identity, designation, effective-date, and route-string information.",
    "AWY_SEG_ALT": "Ordered airway segments, navigation points, courses, changeover points, and altitude constraints.",
    "CDR": "Coded departure route identifiers and their published route strings.",
    "CLS_ARSP": "Airport-linked Class B, C, D, or E airspace configuration and descriptive information.",
    "COM": "Remote communications outlets and related communication facility information.",
    "DP_APT": "Airports and runway ends associated with a departure procedure.",
    "DP_BASE": "Departure procedure identity, controlling ARTCC, and published metadata.",
    "DP_RTE": "Ordered departure-procedure routes, transitions, and route points.",
    "FIX_BASE": "Core fix identity, coordinates, location, use, and controlling-facility information.",
    "FIX_CHRT": "Charts on which a fix is published.",
    "FIX_NAV": "Navaids and radials associated with a fix.",
    "FRQ": "FAA frequency assignments and the facilities or services using them.",
    "FSS_BASE": "Flight Service Station identity, location, communications, and service information.",
    "FSS_RMK": "Remarks associated with a Flight Service Station or one of its fields.",
    "HPF_BASE": "Holding-pattern identity, fix, inbound course, turn direction, and leg geometry.",
    "HPF_CHRT": "Charts on which a holding pattern is published.",
    "HPF_RMK": "Remarks associated with a holding pattern or one of its fields.",
    "HPF_SPD_ALT": "Published speed and altitude restrictions for a holding pattern.",
    "ILS_BASE": "Core instrument landing system identity, runway association, status, category, and localizer information.",
    "ILS_DME": "Distance Measuring Equipment associated with an instrument landing system.",
    "ILS_GS": "Glide-slope transmitter and location information for an instrument landing system.",
    "ILS_MKR": "Marker beacon or locator information associated with an instrument landing system.",
    "ILS_RMK": "Remarks associated with an instrument landing system or one of its components.",
    "LID": "FAA location identifiers and their associated facility, state, country, and controlling organization.",
    "MAA_BASE": "Miscellaneous Activity Area identity, activity type, location, schedule, and operating information.",
    "MAA_CON": "Contacts for a Miscellaneous Activity Area.",
    "MAA_RMK": "Remarks associated with a Miscellaneous Activity Area.",
    "MAA_SHP": "Ordered geometry points defining a Miscellaneous Activity Area.",
    "MIL_OPS": "Military operations and services associated with an airport.",
    "MTR_AGY": "Scheduling and originating agencies associated with a military training route.",
    "MTR_BASE": "Military training route identity, type, direction, altitude, and operating information.",
    "MTR_PT": "Ordered navigation points and segment information for a military training route.",
    "MTR_SOP": "Special operating procedures for a military training route.",
    "MTR_TERR": "Terrain-following and route-width information for military training route segments.",
    "MTR_WDTH": "Published width changes along a military training route.",
    "NAV_BASE": "Core navaid identity, type, name, frequency, location, status, and controlling-facility information.",
    "NAV_CKPT": "Checkpoint information associated with a navaid.",
    "NAV_RMK": "Remarks associated with a navaid or one of its fields.",
    "PFR_BASE": "Preferred-route identity, origin, destination, type, direction, and route text.",
    "PFR_RMT_FMT": "Published route-format variants for a preferred route.",
    "PFR_SEG": "Ordered segments and navigation elements for a preferred route.",
    "PJA_BASE": "Parachute Jump Area identity, center, radius, schedule, and associated airport information.",
    "PJA_CON": "Contacts for a Parachute Jump Area.",
    "RDR": "Radar site identity, location, type, status, and owning-facility information.",
    "STAR_APT": "Airports and runway ends associated with a Standard Terminal Arrival Route.",
    "STAR_BASE": "Standard Terminal Arrival Route identity, controlling ARTCC, and published metadata.",
    "STAR_RTE": "Ordered arrival routes, transitions, and route points.",
    "WXL_BASE": "Weather-reporting location identity, position, and associated facility information.",
    "WXL_SVC": "Weather services published for a weather-reporting location.",
}

DESCRIPTION_OVERRIDES = {
    "RWY_END_INTERSECT_LAHSO": "Identifier of the intersecting runway that defines the land-and-hold-short point.",
    "RWY_END_TDZ_ELEV_DATE": "Date on which the runway-end touchdown-zone elevation was determined.",
    "TDZ_ELEV_SOURCE": "Source used to determine the touchdown-zone elevation.",
    "TIME_OF_USE": "Published time-of-use information for the military training route.",
    "MAG_VARN_HEMIS": "Direction (east or west) of magnetic variation.",
    "STATE": "State or territory name associated with the location identifier.",
    "TAB_NAME": "NASR table name associated with the remark.",
    "REF_COL_NAME": "NASR column name associated with the remark; identifies a general remark when no specific source column applies.",
    "REF_COL_SEQ_NO": "Sequence number of the source record associated with the remark.",
    "REMARK": "Free-form FAA remark text associated with the record or referenced field.",
}

UNIT_PATTERNS = (
    (re.compile(r"\bnautical miles?\b|\bNM\b", re.I), "nautical miles"),
    (re.compile(r"\bfeet MSL\b|\bfoot MSL\b", re.I), "feet MSL"),
    (re.compile(r"\bfeet AGL\b|\bfoot AGL\b", re.I), "feet AGL"),
    (re.compile(r"\bfeet\b|\bfoot\b", re.I), "feet"),
    (re.compile(r"\bkilohertz\b|\bKHZ\b", re.I), "kHz"),
    (re.compile(r"\bmegahertz\b|\bMHZ\b", re.I), "MHz"),
    (re.compile(r"\bknots?\b", re.I), "knots"),
    (re.compile(r"\bacres?\b", re.I), "acres"),
    (re.compile(r"\bdecimal degrees?\b", re.I), "decimal degrees"),
    (re.compile(r"\bdegrees?\b", re.I), "degrees"),
    (re.compile(r"\bpercent(?:age)?\b", re.I), "percent"),
    (re.compile(r"\bhours?\b", re.I), "hours"),
    (re.compile(r"\bminutes?\b", re.I), "minutes"),
    (re.compile(r"\bseconds?\b", re.I), "seconds"),
)


def _clean(value: str) -> str:
    return " ".join(value.replace("\f", " ").split())


def _markdown(value: str) -> str:
    return value.replace("|", "\\|")


def _layout_descriptions(
    pdf: Path, names: set[str], tables: set[str]
) -> dict[tuple[str | None, str], str]:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    aliases = sorted((name.strip() for name in names), key=len, reverse=True)
    marker = re.compile(
        r"^\s*(" + "|".join(re.escape(name) for name in aliases) + r")\s*[–—-]\s*(.*)$",
        re.I,
    )
    table_heading = re.compile(
        r"^\s*("
        + "|".join(re.escape(name) for name in sorted(tables, key=len, reverse=True))
        + r")\s+ordered\b",
        re.I,
    )
    candidates: dict[tuple[str | None, str], list[str]] = defaultdict(list)
    lines = result.stdout.splitlines()
    current_table: str | None = None
    for index, line in enumerate(lines):
        heading = table_heading.match(line)
        if heading:
            current_table = heading.group(1).upper()
        match = marker.match(line)
        if not match:
            continue
        parts = [match.group(2).strip()]
        for following in lines[index + 1 :]:
            if not following.strip() or marker.match(following):
                break
            text = following.strip()
            if "DATA LAYOUT" in text or "FIELD DESCRIPTIONS" in text:
                break
            parts.append(text)
        description = _clean(" ".join(parts)).strip(" -")
        if description:
            candidates[(current_table, match.group(1).strip().upper())].append(
                description
            )
    return {key: max(values, key=len) for key, values in candidates.items() if values}


def _format(faa_type: str, max_length: str, description: str) -> str:
    if faa_type == "VARCHAR":
        suffix = "character" if max_length == "1" else "characters"
        value = f"Text, up to {max_length} {suffix}"
    elif faa_type == "NUMBER":
        value = f"Numeric {max_length} (precision, scale)"
    else:
        value = f"{faa_type} {max_length}".strip()
    date_match = re.search(
        r"(?:format|formatted)\s+['‘\"]?([YMD/.-]{6,})", description, re.I
    )
    if date_match:
        value += f"; {date_match.group(1).upper()}"
    return value


def _units(name: str, description: str) -> str:
    normalized = name.upper()
    unitless = (
        "ID",
        "CODE",
        "NAME",
        "FLAG",
        "TYPE",
        "DATE",
        "YEAR",
        "CITY",
        "STATE",
        "COUNTRY",
        "REMARK",
        "TEXT",
        "SEQ",
        "STATUS",
        "HEMIS",
    )
    if any(token in normalized for token in unitless):
        return "Not applicable"
    if normalized in {"LAT_DECIMAL", "LONG_DECIMAL"}:
        return "decimal degrees"
    for pattern, unit in UNIT_PATTERNS:
        if pattern.search(description):
            return unit
    return "Not specified by FAA"


def _examples(csv_path: Path, columns: list[str], limit: int) -> dict[str, str]:
    examples = {column: "" for column in columns}
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader):
            for column in columns:
                if examples[column]:
                    continue
                value = (row.get(column) or "").strip()
                if value:
                    examples[column] = _clean(value)[:80]
            if all(examples.values()) or (limit and row_number + 1 >= limit):
                break
    return examples


def _slug(name: str) -> str:
    return name.lower().replace("_", "-")


def generate(source: Path, output: Path, cycle: str, sample_rows: int) -> None:
    output.mkdir(parents=True, exist_ok=True)
    tables: list[str] = []
    for schema_path in sorted(source.glob("*_CSV_DATA_STRUCTURE.csv")):
        family = schema_path.name.removesuffix("_CSV_DATA_STRUCTURE.csv")
        pdf = source / f"{family} DATA LAYOUT.pdf"
        if not pdf.is_file():
            raise FileNotFoundError(pdf)
        with schema_path.open(encoding="utf-8-sig", newline="") as handle:
            schema_rows = list(csv.DictReader(handle))
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in schema_rows:
            grouped[row["CSV File"].strip()].append(row)
        descriptions = _layout_descriptions(
            pdf,
            {row["Column Name"].strip() for row in schema_rows},
            set(grouped),
        )
        for table, rows in grouped.items():
            csv_path = source / f"{table}.csv"
            if not csv_path.is_file():
                raise FileNotFoundError(csv_path)
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                actual_columns = next(csv.reader(handle))
            declared = [row["Column Name"].strip() for row in rows]
            by_normalized = {name.strip().upper(): name for name in actual_columns}
            columns = [by_normalized.get(name.upper(), name) for name in declared]
            examples = _examples(csv_path, columns, sample_rows)
            page = [
                f"# `{table}`",
                "",
                TABLE_DESCRIPTIONS[table],
                "",
                f"This page describes the FAA CSV published in the **{cycle}** NASR cycle. ",
                "FAA schemas can change between cycles; inspect the schema file shipped with ",
                "the selected cycle when exact compatibility is required.",
                "",
                "## Columns",
                "",
                "| Column | Description | Format | Units | Nullable | Example value |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for row, column in zip(rows, columns):
                key = row["Column Name"].strip().upper()
                description = (
                    descriptions.get((table, key))
                    or descriptions.get((None, key))
                    or DESCRIPTION_OVERRIDES.get(key)
                )
                if not description:
                    description = f"FAA field `{column}`; no expanded definition is provided in the cycle's data-layout document."
                example = examples[column] or f"No non-empty value in {cycle} cycle"
                page.append(
                    "| "
                    + " | ".join(
                        _markdown(value)
                        for value in (
                            f"`{column}`",
                            description,
                            _format(row["Data Type"], row["Max Length"], description),
                            _units(column, description),
                            row["Nullable"],
                            f"`{example}`",
                        )
                    )
                    + " |"
                )
            page.extend(
                [
                    "",
                    "## Sources",
                    "",
                    f"- `{schema_path.name}` for FAA type, maximum length, and nullability",
                    f"- `{pdf.name}` for FAA field definitions and stated units",
                    f"- `{table}.csv` from the {cycle} cycle for example values",
                    "",
                ]
            )
            (output / f"{_slug(table)}.md").write_text(
                "\n".join(page), encoding="utf-8"
            )
            tables.append(table)

    missing = set(TABLE_DESCRIPTIONS).difference(tables)
    unexpected = set(tables).difference(TABLE_DESCRIPTIONS)
    if missing or unexpected:
        raise RuntimeError(
            f"table-description mismatch: missing={missing}, unexpected={unexpected}"
        )
    index = [
        "# CSV table reference",
        "",
        f"The FAA **{cycle} 28-Day NASR Subscription** contains {len(tables)} operational CSV tables.",
        "Each page below describes one table and lists every column in FAA order,",
        "including its definition, format, units, nullability, and an example value.",
        "",
        "Examples are representative source values, not validation rules. A blank or",
        "unusual value may be valid under the FAA specification. Field definitions and",
        "units are taken from the data-layout documents shipped with the cycle;",
        "**Not specified by FAA** means that the layout does not state a unit.",
        "",
        "```{toctree}",
        ":maxdepth: 1",
        "",
        *(_slug(table) for table in sorted(tables)),
        "```",
        "",
    ]
    (output / "index.md").write_text("\n".join(index), encoding="utf-8")
    print(f"Generated {len(tables)} table pages in {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Extracted FAA *_CSV directory")
    parser.add_argument("--output", type=Path, default=Path("docs/csv-tables"))
    parser.add_argument("--cycle", default="2026-08-06")
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=0,
        help="Maximum rows per table to inspect; 0 scans the complete table",
    )
    args = parser.parse_args()
    generate(args.source, args.output, args.cycle, args.sample_rows)


if __name__ == "__main__":
    main()
