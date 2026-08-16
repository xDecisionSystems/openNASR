import pandas as pd
import pytest

from openNASR.weather import (
    AutomatedWeatherStationRepository,
    WeatherLocationRepository,
)
from openNASR.exceptions import RecordNotFoundError


KEY = ("ORL", "AWOS", "FL", "ORLANDO", "US")


def test_weather_station_uses_its_standalone_composite_key():
    repository = AutomatedWeatherStationRepository(
        {
            "AWOS": pd.DataFrame(
                [
                    dict(
                        zip(
                            (
                                "ASOS_AWOS_ID",
                                "ASOS_AWOS_TYPE",
                                "STATE_CODE",
                                "CITY",
                                "COUNTRY_CODE",
                            ),
                            KEY,
                        ),
                        STATION_NAME="Example AWOS",
                    )
                ]
            )
        }
    )

    assert repository.get(KEY).record["STATION_NAME"] == "Example AWOS"
    with pytest.raises(ValueError, match="weather-station identifiers"):
        repository.get(("ORL",))
    with pytest.raises(RecordNotFoundError):
        repository.get((*KEY[:-1], "CA"))


def test_weather_location_collects_matching_service_records():
    key = ("ORL", "ORLANDO", "FL", "US")
    columns = ("WEA_ID", "CITY", "STATE_CODE", "COUNTRY_CODE")
    repository = WeatherLocationRepository(
        {
            "WXL_BASE": pd.DataFrame([dict(zip(columns, key))]),
            "WXL_SVC": pd.DataFrame(
                [dict(zip(columns, key), WEA_SVC_TYPE_CODE="METAR")]
            ),
        }
    )

    assert repository.get(key).services[0]["WEA_SVC_TYPE_CODE"] == "METAR"
