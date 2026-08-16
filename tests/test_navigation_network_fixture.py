import json
from pathlib import Path

import pandas as pd
import pytest

from openNASR.airway import AirwayRepository
from openNASR.communications import CommunicationOutletRepository, FrequencyRepository
from openNASR.exceptions import AmbiguousRecordError
from openNASR.holding import HoldingPatternRepository


def test_navigation_network_types_are_publicly_exported():
    from openNASR import (
        Airway,
        AirwayRecord,
        AirwayRepository,
        AirwaySegmentRecord,
        CommunicationOutlet,
        CommunicationOutletRecord,
        CommunicationOutletRepository,
        Frequency,
        FrequencyRecord,
        FrequencyRepository,
        HoldingPattern,
        HoldingPatternChartRecord,
        HoldingPatternRecord,
        HoldingPatternRemarkRecord,
        HoldingPatternRepository,
        HoldingPatternSpeedAltitudeRecord,
    )

    assert all(
        isinstance(item, type)
        for item in (
            Airway,
            AirwayRecord,
            AirwayRepository,
            AirwaySegmentRecord,
            CommunicationOutlet,
            CommunicationOutletRecord,
            CommunicationOutletRepository,
            Frequency,
            FrequencyRecord,
            FrequencyRepository,
            HoldingPattern,
            HoldingPatternChartRecord,
            HoldingPatternRecord,
            HoldingPatternRemarkRecord,
            HoldingPatternRepository,
            HoldingPatternSpeedAltitudeRecord,
        )
    )


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "relationships" / "navigation_network.json"
)


def _repositories(schema_id: str):
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))[schema_id]
    tables = {name: pd.DataFrame(values) for name, values in rows.items()}
    return (
        AirwayRepository(tables),
        HoldingPatternRepository(tables),
        CommunicationOutletRepository(tables),
        FrequencyRepository(tables),
    )


@pytest.mark.parametrize("schema_id", ("pre_2026_09", "nasr_2026_09"))
def test_navigation_network_fixture_preserves_order_and_complete_keys(schema_id):
    airways, holding_patterns, _outlets, frequencies = _repositories(schema_id)

    airway = airways.get(("Y", "D", "1"))
    holding_pattern = holding_patterns.get(("ALPHA", "1", "FL", "US"))
    frequency = frequencies.get(
        ("ALPHA", "A1", "A", "FL", "US", "121.5", None, "EMERGENCY")
    )

    assert [segment["FROM_POINT"] for segment in airway.segments] == [
        "ALPHA",
        "BRAVO",
    ]
    assert airway.segments[0].minimum_enroute_altitude == 5000
    assert airway.segments[0].fix is not None
    assert airway.segments[1].navaid is not None
    assert [remark["REMARK"] for remark in holding_pattern.remarks] == [
        "first",
        "second",
    ]
    assert holding_pattern.fix is not None
    assert holding_pattern.speed_altitude_limits[0].altitude == "6000"
    assert frequency.record.serviced_facility_key == ("A1", "A", "FL", "US")
    assert len(frequencies.find(serviced_facility=("A1", "A", "FL", "US"))) == 1


@pytest.mark.parametrize("schema_id", ("pre_2026_09", "nasr_2026_09"))
def test_navigation_network_fixture_reports_ambiguous_short_communication_ids(
    schema_id,
):
    _airways, _holding_patterns, outlets, _frequencies = _repositories(schema_id)

    with pytest.raises(AmbiguousRecordError) as raised:
        outlets.get("DUP")

    assert len(raised.value.candidates) == 2
