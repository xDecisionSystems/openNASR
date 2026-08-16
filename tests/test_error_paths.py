"""Error handling for malformed and incomplete synthetic NASR cycles."""

import pytest

from openNASR import Airport
from openNASR.exceptions import SchemaMismatchError


def test_missing_airport_identifier_raises_schema_mismatch(make_nasr_from_fixture):
    with pytest.raises(SchemaMismatchError) as error:
        make_nasr_from_fixture("malformed")

    assert error.value.table == "APT_BASE"
    assert error.value.missing_columns == ("ARPT_ID",)


def test_missing_optional_marker_table_leaves_markers_empty(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("missing_table_cycle")

    airport = Airport("BWI", nasr)

    assert airport.ils.ids == ["10"]
    assert airport.mkr.ids == []
