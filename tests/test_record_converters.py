from datetime import date
from decimal import Decimal
from enum import Enum

import pytest

from openNASR.records import (
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
    with pytest.raises(ValueError, match="Unsupported boolean code"):
        boolean("MAYBE")
