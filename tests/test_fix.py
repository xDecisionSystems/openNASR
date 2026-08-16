"""Fix lookups use the deterministic core fixture."""

from openNASR import FIX


def test_lookup_unique_fix(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    fix = FIX("AABEE", nasr)

    assert fix.FIX_ID == "AABEE"
