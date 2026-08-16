"""Airport-linked class-airspace and military-operation behavior."""

import json
from pathlib import Path

import pandas as pd
import pytest

from openNASR import (
    ClassAirspace,
    ClassAirspaceRecord as ExportedClassAirspaceRecord,
    ClassAirspaceRepository as ExportedClassAirspaceRepository,
    MilitaryOperation,
    MilitaryOperationRecord as ExportedMilitaryOperationRecord,
    MilitaryOperationRepository as ExportedMilitaryOperationRepository,
)
from openNASR.airspace import ClassAirspaceRepository
from openNASR.exceptions import AmbiguousRecordError, RecordNotFoundError
from openNASR.military import MilitaryOperationRepository
from openNASR.records import ClassAirspaceRecord, MilitaryOperationRecord
from openNASR.repository import AirportRepository


RELATIONSHIPS = (
    Path(__file__).parent / "fixtures" / "relationships" / "airport_linked.json"
)


def test_airport_linked_public_types_are_exported():
    assert ExportedClassAirspaceRecord is ClassAirspaceRecord
    assert ExportedClassAirspaceRepository is ClassAirspaceRepository
    assert ExportedMilitaryOperationRecord is MilitaryOperationRecord
    assert ExportedMilitaryOperationRepository is MilitaryOperationRepository
    assert ClassAirspace.__name__ == "ClassAirspace"
    assert MilitaryOperation.__name__ == "MilitaryOperation"


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


def test_military_operation_record_retains_raw_row_and_typed_fields():
    record = MilitaryOperationRecord(
        {
            "SITE_NO": "00000001A",
            "SITE_TYPE_CODE": "A",
            "ARPT_ID": "DUP",
            "MIL_OPS_OPER_CODE": "M",
            "MIL_OPS_CALL": "TEST OPS",
            "MIL_OPS_HRS": "",
        }
    )

    assert record.raw["MIL_OPS_OPER_CODE"] == "M"
    assert record.airport_site_key == ("00000001A", "A")
    assert record.operating_code == "M"
    assert record.call_sign == "TEST OPS"
    assert record.operating_hours is None


@pytest.mark.parametrize("schema_id", ("pre_2026_09", "nasr_2026_09"))
def test_airport_linked_repositories_find_and_get_both_schema_rows(schema_id):
    rows = json.loads(RELATIONSHIPS.read_text(encoding="utf-8"))[schema_id]
    tables = {
        table_name: pd.DataFrame(table_rows) for table_name, table_rows in rows.items()
    }
    tables["APT_BASE"]["ICAO_ID"] = ""

    class_airspaces = ClassAirspaceRepository(tables)
    military_operations = MilitaryOperationRepository(tables)
    first_airport = rows["APT_BASE"][0]
    key = (first_airport["SITE_NO"], first_airport["SITE_TYPE_CODE"])

    assert len(class_airspaces.find(airport_id="DUP")) == 2
    assert len(military_operations.find(airport_id="DUP")) == 2
    assert class_airspaces.get(key).airport_site_key == key
    assert military_operations.get(key).airport_site_key == key


@pytest.mark.parametrize(
    "repository_type, table_name",
    (
        (ClassAirspaceRepository, "CLS_ARSP"),
        (MilitaryOperationRepository, "MIL_OPS"),
    ),
)
def test_airport_linked_repositories_raise_for_missing_and_ambiguous_site_keys(
    repository_type, table_name
):
    tables = _nasr_tables()
    repository = repository_type(tables)
    key = ("00000001A", "A")

    with pytest.raises(RecordNotFoundError):
        repository.get(("missing", "a"))

    tables[table_name] = pd.concat([tables[table_name], tables[table_name]])
    with pytest.raises(AmbiguousRecordError):
        repository_type(tables).get(key)


def test_missing_airport_linked_rows_leave_optional_relationships_empty():
    tables = _nasr_tables()
    tables["APT_BASE"] = pd.concat(
        [
            tables["APT_BASE"],
            pd.DataFrame(
                [
                    {
                        "ARPT_ID": "NONE",
                        "ICAO_ID": "KNON",
                        "SITE_NO": "00000009A",
                        "SITE_TYPE_CODE": "A",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    airport = AirportRepository(tables).get("KNON")

    assert airport.class_airspace is None
    assert airport.military_operations == ()
