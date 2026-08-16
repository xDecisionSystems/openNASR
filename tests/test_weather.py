import pandas as pd
import pytest

from openNASR.weather import AutomatedWeatherStationRepository
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
