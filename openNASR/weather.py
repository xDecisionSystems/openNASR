"""Rich access to FAA weather-station records."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import AutomatedWeatherStationRecord


WEATHER_STATION_KEY = (
    "ASOS_AWOS_ID",
    "ASOS_AWOS_TYPE",
    "STATE_CODE",
    "CITY",
    "COUNTRY_CODE",
)


class AutomatedWeatherStation:
    """One standalone FAA automated weather-station record."""

    def __init__(self, record: AutomatedWeatherStationRecord) -> None:
        self.record = record


class AutomatedWeatherStationRepository:
    """Look up weather stations by their complete verified FAA key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, ...]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            WEATHER_STATION_KEY
        ):
            raise ValueError(
                "Automated weather-station identifiers require "
                f"({', '.join(WEATHER_STATION_KEY)})"
            )
        return identifier

    def _matching(self, frame: DataFrame, key: tuple[object, ...]) -> DataFrame:
        rows = frame
        for column, value in zip(WEATHER_STATION_KEY, key):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return rows

    def find(
        self, identifier: object | None = None
    ) -> tuple[AutomatedWeatherStation, ...]:
        rows = self._nasr["AWOS"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(
            AutomatedWeatherStation(AutomatedWeatherStationRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object) -> AutomatedWeatherStation:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="AutomatedWeatherStation", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="AutomatedWeatherStation",
                identifier=identifier,
                candidates=records,
            )
        return records[0]


__all__ = ["AutomatedWeatherStation", "AutomatedWeatherStationRepository"]
