"""Ensure default tests remain independent of network services."""

import ast
from pathlib import Path


NETWORK_MODULE_ROOTS = frozenset(
    {
        "aiohttp",
        "ftplib",
        "http",
        "httpx",
        "requests",
        "socket",
        "telnetlib",
        "urllib",
        "websocket",
    }
)


def test_test_suite_does_not_import_network_clients():
    tests_root = Path(__file__).parent
    sources = [tests_root / "conftest.py", *sorted(tests_root.glob("test_*.py"))]

    imported_roots = set()
    for source in sources:
        module = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

    assert not imported_roots & NETWORK_MODULE_ROOTS
