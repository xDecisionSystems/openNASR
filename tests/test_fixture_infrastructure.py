from __future__ import annotations


def test_core_fixture_loads_without_package_data(make_nasr_from_fixture):
    nasr, cache_root = make_nasr_from_fixture("core/pre_2026_09")

    assert cache_root.is_dir()
    assert set(nasr) == {
        "APT_BASE",
        "APT_RWY",
        "APT_RWY_END",
        "ILS_BASE",
        "ILS_DME",
        "ILS_GS",
        "ILS_MKR",
        "FIX_BASE",
        "NAV_BASE",
        "ARB_BASE",
        "ARB_SEG",
    }
    assert set(nasr["APT_BASE"]["ARPT_ID"]) == {"BWI", "DCA"}
    assert len(nasr["NAV_BASE"].query("NAV_ID == 'DUP'")) == 2


def test_schema_only_fixture_loads_every_csv(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("schema_only/nasr_2026_09")

    assert len(nasr) == 87
    assert nasr["APT_RWY"].empty
    assert nasr["APT_RWY"].columns.tolist()[13:15] == [
        "PAVEMENT_CLASSIFICATION",
        "PCN_PCR_NUMBER",
    ]
