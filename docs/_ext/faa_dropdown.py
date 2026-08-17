"""Accessible, dependency-free collapsible content for FAA record fields."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from docutils import nodes
from docutils.parsers.rst import Directive

from openNASR.registry import RICH_RECORD_TYPES


class FaaDropdownDirective(Directive):
    """Render directive content inside native HTML details/summary elements."""

    has_content = True
    required_arguments = 1
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:
        self.assert_has_content()
        title = escape(self.arguments[0])
        content = nodes.container(classes=["faa-record-fields-content"])
        self.state.nested_parse(self.content, self.content_offset, content)
        return [
            nodes.raw(
                "",
                f'<details class="faa-record-fields"><summary>{title}</summary>',
                format="html",
            ),
            content,
            nodes.raw("", "</details>", format="html"),
        ]


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
        field = cells[0].strip().strip("`")
        description = cells[1].strip().replace(r"\|", "|")
        rows.append((field, description))
    if not rows:
        raise ValueError(f"No field rows found in {csv_page}")
    return rows


def _rst_text(value: str) -> str:
    """Escape the small set of inline RST markers found in FAA prose."""

    return (
        value.replace("\\", r"\\")
        .replace("`", "'")
        .replace("_", r"\_")
        .replace("*", r"\*")
    )


def _append_record_fields(
    app: Any,
    what: str,
    _name: str,
    obj: object,
    _options: object,
    lines: list[str],
) -> None:
    """Attach the matching FAA table's raw fields to an autodoc class entry."""

    if what != "class":
        return
    table = next(
        (
            table_name
            for table_name, record_type in RICH_RECORD_TYPES.items()
            if obj is record_type
        ),
        None,
    )
    if table is None:
        return
    slug = _slug(table)
    rows = _field_rows(Path(app.confdir) / "csv-tables" / f"{slug}.md")
    class_name = type(obj).__name__ if not isinstance(obj, type) else obj.__name__
    lines.extend(
        [
            "",
            f".. faa-dropdown:: {class_name} raw fields — {table} ({len(rows)})",
            "",
            f"   ``{class_name}`` preserves one complete ``{table}`` row. Fields are",
            "   available by mapping key or attribute name even when the class does",
            "   not declare a dedicated typed property for each one.",
            "",
            "   .. list-table::",
            "      :header-rows: 1",
            "      :widths: 25 75",
            "",
            "      * - Field",
            "        - Description",
        ]
    )
    for field, description in rows:
        lines.extend(
            [
                f"      * - ``{field}``",
                f"        - {_rst_text(description)}",
            ]
        )
    lines.extend(
        [
            "",
            f"   See :doc:`the complete {table} column reference </csv-tables/{slug}>`",
            "   for formats, units, nullability, and example values.",
        ]
    )


def setup(app: Any) -> dict[str, bool]:
    app.add_directive("faa-dropdown", FaaDropdownDirective)
    app.connect("autodoc-process-docstring", _append_record_fields)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
