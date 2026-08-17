"""Ensure default tests remain independent of network services."""

import ast
import os
from pathlib import Path
import subprocess
import sys


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


def test_importing_package_does_not_check_the_network(tmp_path):
    """A library import must not contact FAA or any other remote service."""

    script = """
import urllib.request

calls = []

def opener(*args, **kwargs):
    calls.append((args, kwargs))
    raise AssertionError("network access attempted during import")

urllib.request.urlopen = opener
import openNASR
assert calls == [], calls
"""
    environment = {
        **os.environ,
        "OPENNASR_CACHE_DIR": str(tmp_path / "cache"),
        "PYTHONPATH": str(Path(__file__).parents[1]),
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
