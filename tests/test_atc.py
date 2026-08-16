import pandas as pd
import pytest

from openNASR.atc import AtcFacilityRepository
from openNASR.exceptions import RecordNotFoundError


KEY = ("123", "ATCT", "TOWER", "FL", "ABC", "ORLANDO", "US")


def row(**extra):
    return dict(
        zip(
            (
                "SITE_NO",
                "SITE_TYPE_CODE",
                "FACILITY_TYPE",
                "STATE_CODE",
                "FACILITY_ID",
                "CITY",
                "COUNTRY_CODE",
            ),
            KEY,
        ),
        **extra,
    )


def test_atc_facility_collects_matching_child_records_in_remark_order():
    repository = AtcFacilityRepository(
        {
            "ATC_BASE": pd.DataFrame([row(FACILITY_NAME="Example Tower")]),
            "ATC_ATIS": pd.DataFrame([row(ATIS_NO="1", TEXT="Arrival information")]),
            "ATC_RMK": pd.DataFrame(
                [row(REMARK_NO="2", TEXT="Second"), row(REMARK_NO="1", TEXT="First")]
            ),
            "ATC_SVC": pd.DataFrame([row(CTL_SVC="APP", SERVICE="Approach")]),
        }
    )

    facility = repository.get(KEY)

    assert facility.record["FACILITY_NAME"] == "Example Tower"
    assert facility.atis_services[0]["TEXT"] == "Arrival information"
    assert [remark["TEXT"] for remark in facility.remarks] == ["First", "Second"]
    assert facility.services[0]["SERVICE"] == "Approach"


def test_atc_facility_requires_full_key_and_reports_missing_records():
    repository = AtcFacilityRepository({"ATC_BASE": pd.DataFrame([row()])})

    with pytest.raises(ValueError, match="ATC facility identifiers"):
        repository.get(("ABC",))
    with pytest.raises(RecordNotFoundError):
        repository.get((*KEY[:-1], "CA"))
