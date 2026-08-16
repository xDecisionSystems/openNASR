import openNASR
from openNASR.cycles import CycleManager


def test_cycle_manager_is_public_package_export():
    assert openNASR.CycleManager is CycleManager
    assert "CycleManager" in openNASR.__all__
