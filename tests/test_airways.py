import json
from pathlib import Path

import pandas as pd

from openNASR.airway import AirwayRepository


def test_airway_repository_orders_segments_and_exposes_altitudes():
    path = Path(__file__).parent / "fixtures" / "relationships" / "airways.json"
    rows = json.loads(path.read_text(encoding="utf-8"))["pre_2026_09"]
    rows["AWY_SEG_ALT"][0]["MIN_ENROUTE_ALT"] = "5000"
    repository = AirwayRepository(
        {name: pd.DataFrame(values) for name, values in rows.items()}
    )

    airway = repository.get(("Y", "D", "1"))

    assert [segment["FROM_POINT"] for segment in airway.segments] == ["ALPHA", "BRAVO"]
    assert airway.segments[1].minimum_enroute_altitude == 5000
