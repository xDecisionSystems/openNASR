"""Navaid lookups use the deterministic core fixture."""

from openNASR import NAVAID


def test_lookup_unique_navaid(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    navaid = NAVAID("UNIQ", nasr)

    assert navaid.NAV_ID == "UNIQ"
