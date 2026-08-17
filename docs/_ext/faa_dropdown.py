"""Accessible, dependency-free collapsible content for FAA record fields."""

from __future__ import annotations

from html import escape
from typing import Any

from docutils import nodes
from docutils.parsers.rst import Directive


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


def setup(app: Any) -> dict[str, bool]:
    app.add_directive("faa-dropdown", FaaDropdownDirective)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
