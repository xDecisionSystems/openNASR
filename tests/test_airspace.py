"""ARTCC access uses the deterministic core fixture."""


def test_load_artcc_and_access_high_boundary(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("core/pre_2026_09")

    nasr.loadARTCC()
    zob = nasr.artcc.getARTCC("ZOB")

    assert zob is not None
    assert zob.high.getShape.is_valid
    assert zob.low.getShape.is_valid
