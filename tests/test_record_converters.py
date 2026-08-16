from datetime import date
from decimal import Decimal
from enum import Enum

import pytest

from openNASR.exceptions import FieldConversionError
from openNASR.records import (
    FaaRecord,
    FieldContext,
    boolean,
    coordinate,
    decimal,
    enum_value,
    float_value,
    integer,
    iso_date,
    nullable_text,
)


class Surface(Enum):
    ASPHALT = "A"
    CONCRETE = "C"


class TypedRunway(FaaRecord):
    @property
    def sequence(self) -> int | None:
        return integer(
            self["SEQUENCE"],
            context=FieldContext(table="RWY", column="SEQUENCE"),
        )

    @property
    def width(self) -> int | None:
        return integer(
            self["WIDTH"],
            context=FieldContext(table="RWY", column="WIDTH"),
        )


def test_shared_converters_return_typed_values_without_altering_raw_text():
    raw = {
        "TEXT": "  O'Hare  ",
        "DATE": "2026-09-03",
        "IDENTIFIER": "0012",
        "DECIMAL": "12.340",
        "FLOAT": "12.5",
        "ACTIVE": " y ",
        "LATITUDE": "28.5383",
        "SURFACE": "A",
    }

    assert nullable_text(raw["TEXT"]) == "  O'Hare  "
    assert iso_date(raw["DATE"]) == date(2026, 9, 3)
    assert integer(raw["IDENTIFIER"]) == 12
    assert decimal(raw["DECIMAL"]) == Decimal("12.340")
    assert float_value(raw["FLOAT"]) == 12.5
    assert boolean(raw["ACTIVE"]) is True
    assert coordinate(raw["LATITUDE"]) == 28.5383
    assert enum_value(raw["SURFACE"], Surface) is Surface.ASPHALT
    assert raw["IDENTIFIER"] == "0012"
    assert raw["TEXT"] == "  O'Hare  "


@pytest.mark.parametrize(
    ("converter", "arguments"),
    [
        (nullable_text, ()),
        (iso_date, ()),
        (integer, ()),
        (decimal, ()),
        (float_value, ()),
        (boolean, ()),
        (coordinate, ()),
        (enum_value, (Surface,)),
    ],
)
def test_shared_converters_return_none_for_an_empty_field(converter, arguments):
    assert converter("", *arguments) is None


def test_boolean_rejects_unknown_nonempty_code():
    context = FieldContext(
        cycle="2026-09-03",
        table="APT_BASE",
        column="ACTIVE",
        record_identity={"ARPT_ID": "0012"},
    )

    with pytest.raises(FieldConversionError) as raised:
        boolean("MAYBE", context=context)

    error = raised.value
    assert error.cycle == "2026-09-03"
    assert error.table == "APT_BASE"
    assert error.column == "ACTIVE"
    assert error.raw_value == "MAYBE"
    assert error.record_identity == {"ARPT_ID": "0012"}
    assert error.expected_type is bool
    assert "APT_BASE.ACTIVE" in str(error)
    assert "MAYBE" in str(error)


def test_typed_properties_do_not_change_leading_zero_or_empty_raw_fields():
    record = TypedRunway({"SEQUENCE": "0012", "WIDTH": ""})

    assert record.raw["SEQUENCE"] == "0012"
    assert record.raw["WIDTH"] == ""
    assert record.sequence == 12
    assert record.width is None
    assert record.raw["SEQUENCE"] == "0012"
    assert record.raw["WIDTH"] == ""
