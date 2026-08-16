import pandas as pd
import pytest

from openNASR.locations import LocationIdentifierRepository


def test_location_identifier_uses_full_composite_key():
    columns = (
        "COUNTRY_CODE",
        "LOC_ID",
        "REGION_CODE",
        "STATE",
        "CITY",
        "LID_GROUP",
        "FAC_TYPE",
    )
    key = ("US", "ORL", "ASO", "FL", "ORLANDO", "FAA", "ARPT")
    repository = LocationIdentifierRepository(
        {"LID": pd.DataFrame([dict(zip(columns, key))])}
    )

    assert repository.get(key).record["LOC_ID"] == "ORL"
    with pytest.raises(ValueError, match="Location-identifier identifiers"):
        repository.get(("ORL",))
