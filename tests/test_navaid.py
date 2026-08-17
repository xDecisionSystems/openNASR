"""Navaid lookups use the deterministic core fixture."""

import pandas as pd
import pytest

from openNASR import NAVAID
from openNASR.exceptions import RecordNotFoundError


def test_lookup_unique_navaid(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    navaid = NAVAID("UNIQ", nasr)

    assert navaid.NAV_ID == "UNIQ"


class _FakeNasr(dict):
    def isNavaid(self, nav):
        return nav in self["NAV_BASE"]["NAV_ID"].to_list()


def test_legacy_navaid_incountry_filters_the_same_column_as_the_modern_repository():
    """``inCountry`` must mean COUNTRY_CODE, matching NavaidRepository's `country`."""
    nasr = _FakeNasr(
        NAV_BASE=pd.DataFrame(
            [
                {
                    "NAV_ID": "DUP",
                    "NAV_TYPE": "VOR",
                    "STATE_CODE": "MD",
                    "COUNTRY_CODE": "US",
                    "COUNTRY_NAME": "UNITED STATES",
                    "HIGH_ALT_ARTCC_ID": "ZDC",
                    "LOW_ALT_ARTCC_ID": "ZDC",
                },
                {
                    "NAV_ID": "DUP",
                    "NAV_TYPE": "VOR",
                    "STATE_CODE": "ON",
                    "COUNTRY_CODE": "CA",
                    "COUNTRY_NAME": "CANADA",
                    "HIGH_ALT_ARTCC_ID": "ZDC",
                    "LOW_ALT_ARTCC_ID": "ZDC",
                },
            ]
        )
    )

    navaid = NAVAID("DUP", nasr, inCountry="US")

    assert navaid.STATE_CODE == "MD"

    with pytest.raises(RecordNotFoundError):
        NAVAID("DUP", nasr, inCountry="UNITED STATES")
