"""Rich access to standalone FAA communication and frequency tables."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FaaRecord, NavaidRecord, nullable_text
from .relationships import related_record

SERVICED_FACILITY_KEY = (
    "SERVICED_FACILITY",
    "SERVICED_SITE_TYPE",
    "SERVICED_STATE",
    "SERVICED_COUNTRY",
)
FREQUENCY_KEY = (
    "FACILITY",
    *SERVICED_FACILITY_KEY,
    "FREQ",
    "SECTORIZATION",
    "FREQ_USE",
)


class CommunicationOutletRecord(FaaRecord):
    """Typed conveniences for a standalone ``COM`` communication outlet."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def identifier(self) -> str | None:
        return self._text("COMM_LOC_ID")

    @property
    def name(self) -> str | None:
        return self._text("COMM_OUTLET_NAME")

    @property
    def communication_type(self) -> str | None:
        return self._text("COMM_TYPE")


class FrequencyRecord(FaaRecord):
    """Typed conveniences for a standalone ``FRQ`` frequency assignment."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def frequency_key(
        self,
    ) -> (
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            str,
            str | None,
            str,
        ]
        | None
    ):
        facility = self._text("FACILITY")
        frequency = self._text("FREQ")
        frequency_use = self._text("FREQ_USE")
        if facility is None or frequency is None or frequency_use is None:
            return None
        return (
            facility,
            self._text("SERVICED_FACILITY"),
            self._text("SERVICED_SITE_TYPE"),
            self._text("SERVICED_STATE"),
            self._text("SERVICED_COUNTRY"),
            frequency,
            self._text("SECTORIZATION"),
            frequency_use,
        )

    @property
    def serviced_facility_key(
        self,
    ) -> tuple[str, str, str | None, str | None] | None:
        facility = self._text("SERVICED_FACILITY")
        site_type = self._text("SERVICED_SITE_TYPE")
        if facility is None or site_type is None:
            return None
        return (
            facility,
            site_type,
            self._text("SERVICED_STATE"),
            self._text("SERVICED_COUNTRY"),
        )

    @property
    def facility(self) -> str | None:
        return self._text("FACILITY")

    @property
    def frequency(self) -> str | None:
        return self._text("FREQ")


class CommunicationOutlet:
    """One communication-outlet record."""

    def __init__(
        self, record: CommunicationOutletRecord, *, navaid: NavaidRecord | None
    ) -> None:
        self.record = record
        self.navaid = navaid


class CommunicationOutletRepository:
    """Look up communication outlets by their FAA communication location ID."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def find(self, identifier: str | None = None) -> tuple[CommunicationOutlet, ...]:
        rows = self._nasr["COM"]
        if identifier is not None:
            rows = rows[
                rows["COMM_LOC_ID"]
                .map(self._normalized)
                .eq(self._normalized(identifier))
            ]
        return tuple(
            CommunicationOutlet(
                CommunicationOutletRecord(row),
                navaid=related_record(
                    self._nasr,
                    source=row,
                    target_table="NAV_BASE",
                    columns=(
                        ("NAV_ID", "NAV_ID"),
                        ("NAV_TYPE", "NAV_TYPE"),
                        ("CITY", "CITY"),
                        ("STATE_CODE", "STATE_CODE"),
                        ("COUNTRY_CODE", "COUNTRY_CODE"),
                    ),
                    record_type=NavaidRecord,
                    relationship="communication-outlet navaid",
                ),
            )
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: str) -> CommunicationOutlet:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="CommunicationOutlet", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="CommunicationOutlet",
                identifier=identifier,
                candidates=records,
            )
        return records[0]


class Frequency:
    """One frequency-assignment record."""

    def __init__(self, record: FrequencyRecord) -> None:
        self.record = record


class FrequencyRepository:
    """Look up frequency assignments by their complete FAA composite key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, ...]:
        if not isinstance(identifier, tuple) or len(identifier) != len(FREQUENCY_KEY):
            raise ValueError(
                f"Frequency identifiers require ({', '.join(FREQUENCY_KEY)})"
            )
        return identifier

    def _matching(
        self,
        frame: DataFrame,
        key: tuple[object, ...],
        *,
        columns: tuple[str, ...] = FREQUENCY_KEY,
    ) -> DataFrame:
        rows = frame
        for column, value in zip(columns, key):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return rows

    def find(
        self,
        identifier: object | None = None,
        *,
        serviced_facility: tuple[object, object, object, object] | None = None,
    ) -> tuple[Frequency, ...]:
        rows = self._nasr["FRQ"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        if serviced_facility is not None:
            if not isinstance(serviced_facility, tuple) or len(
                serviced_facility
            ) != len(SERVICED_FACILITY_KEY):
                raise ValueError(
                    "Serviced-facility filters require "
                    f"({', '.join(SERVICED_FACILITY_KEY)})"
                )
            rows = self._matching(
                rows, serviced_facility, columns=SERVICED_FACILITY_KEY
            )
        return tuple(
            Frequency(FrequencyRecord(row)) for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object) -> Frequency:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(entity_type="Frequency", identifier=identifier)
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="Frequency", identifier=identifier, candidates=records
            )
        return records[0]


__all__ = [
    "CommunicationOutlet",
    "CommunicationOutletRepository",
    "Frequency",
    "FrequencyRepository",
]
