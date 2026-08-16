"""Class-airspace records use the verified airport site relationship."""

import pandas as pd

from openNASR.airspace import ClassAirspaceRepository
from openNASR.records import ClassAirspaceRecord
from openNASR.military import MilitaryOperationRepository
from openNASR.repository import AirportRepository


def _nasr_tables():
    return {
        "APT_BASE": pd.DataFrame(
            [
                {
                    "ARPT_ID": "DUP",
                    "ICAO_ID": "KDUP",
                    "SITE_NO": "00000001A",
                    "SITE_TYPE_CODE": "A",
                }
            ]
        ),
        "CLS_ARSP": pd.DataFrame(
            [
                {
                    "SITE_NO": "00000001A",
                    "SITE_TYPE_CODE": "A",
                    "ARPT_ID": "DUP",
                    "CLASS_B_AIRSPACE": "",
                    "CLASS_C_AIRSPACE": "Y",
                    "CLASS_D_AIRSPACE": "",
                    "CLASS_E_AIRSPACE": "Y",
                }
            ]
        ),
        "MIL_OPS": pd.DataFrame(
            [
                {
                    "SITE_NO": "00000001A",
                    "SITE_TYPE_CODE": "A",
                    "ARPT_ID": "DUP",
                    "MIL_OPS_OPER_CODE": "M",
                    "MIL_OPS_CALL": "TEST OPS",
                    "MIL_OPS_HRS": "H24",
                }
            ]
        ),
    }


def test_class_airspace_record_retains_raw_row_and_typed_site_key():
    record = ClassAirspaceRecord(_nasr_tables()["CLS_ARSP"].iloc[0].to_dict())

    assert record.raw["CLASS_C_AIRSPACE"] == "Y"
    assert record.airport_site_key == ("00000001A", "A")
    assert record.classes == {"B": None, "C": "Y", "D": None, "E": "Y"}


def test_class_airspace_repository_and_airport_use_the_site_key():
    tables = _nasr_tables()

    class_airspace = ClassAirspaceRepository(tables).get(("00000001a", "a"))
    airport = AirportRepository(tables).get("kdup")

    assert class_airspace.airport_site_key == ("00000001A", "A")
    assert airport.class_airspace is not None
    assert airport.class_airspace.airport_site_key == class_airspace.airport_site_key


def test_military_operations_attach_to_airport_by_site_key():
    tables = _nasr_tables()

    operation = MilitaryOperationRepository(tables).get(("00000001a", "a"))
    airport = AirportRepository(tables).get("kdup")

    assert operation.call_sign == "TEST OPS"
    assert tuple(item.call_sign for item in airport.military_operations) == (
        operation.call_sign,
    )
