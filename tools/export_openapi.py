"""Write the API's OpenAPI document to ``docs/openapi.json``.

Run this after any API change; ``tests/test_api_contract.py`` fails when the
committed file is out of date, so the published contract changes on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).parents[1]
sys.path[:0] = [str(ROOT / "core"), str(ROOT / "contract"), str(ROOT / "api")]

from openNASR_api import CycleStore, create_app  # noqa: E402

OUTPUT = ROOT / "docs" / "openapi.json"


def build_document() -> dict:
    with tempfile.TemporaryDirectory() as empty:
        app = create_app(CycleStore(Path(empty)), ["export"])
        return app.openapi()


def render() -> str:
    return json.dumps(build_document(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
