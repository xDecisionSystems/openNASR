import pandas as pd

from openNASR.fss import FlightServiceStationRepository


def test_flight_service_station_collects_ordered_remarks():
    key = ("ORL", "ORLANDO", "ORLANDO", "FL", "US")
    columns = ("FSS_ID", "NAME", "CITY", "STATE_CODE", "COUNTRY_CODE")
    repository = FlightServiceStationRepository(
        {
            "FSS_BASE": pd.DataFrame([dict(zip(columns, key))]),
            "FSS_RMK": pd.DataFrame(
                [
                    dict(zip(columns, key), REF_COL_NAME="TEXT", REF_COL_SEQ_NO="2"),
                    dict(zip(columns, key), REF_COL_NAME="TEXT", REF_COL_SEQ_NO="1"),
                ]
            ),
        }
    )

    assert [remark["REF_COL_SEQ_NO"] for remark in repository.get(key).remarks] == [
        "1",
        "2",
    ]
