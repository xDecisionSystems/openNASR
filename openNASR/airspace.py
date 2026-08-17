"""Rich objects for FAA airspace tables: airport-linked class airspace and
ARTCC boundaries."""

from __future__ import annotations

from collections.abc import Mapping

from pandas import DataFrame

from .arb import Boundary
from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FaaRecord, nullable_text

AIRPORT_SITE_KEY = ("SITE_NO", "SITE_TYPE_CODE")


class ClassAirspaceRecord(FaaRecord):
    """Typed conveniences for one airport-linked class-airspace row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def site_no(self) -> str | None:
        return self._text("SITE_NO")

    @property
    def site_type_code(self) -> str | None:
        return self._text("SITE_TYPE_CODE")

    @property
    def airport_id(self) -> str | None:
        return self._text("ARPT_ID")

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        """Verified key shared with the corresponding ``APT_BASE`` row."""

        if self.site_no is None or self.site_type_code is None:
            return None
        return self.site_no, self.site_type_code

    @property
    def classes(self) -> Mapping[str, str | None]:
        """Raw FAA class-airspace codes keyed by class letter."""

        return {
            letter: self._text(f"CLASS_{letter}_AIRSPACE")
            for letter in ("B", "C", "D", "E")
        }


class ClassAirspace:
    """Rich view of a ``CLS_ARSP`` row linked to one airport site."""

    def __init__(self, record: ClassAirspaceRecord) -> None:
        self.record = record

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        return self.record.airport_site_key

    @property
    def airport_id(self) -> str | None:
        return self.record.airport_id

    @property
    def classes(self) -> Mapping[str, str | None]:
        return self.record.classes


class ClassAirspaceRepository:
    """Lookup class-airspace records by their verified airport-site key."""

    entity_type = "ClassAirspace"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["CLS_ARSP"]

    def _site_key(self, identifier: object) -> tuple[object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            AIRPORT_SITE_KEY
        ):
            columns = ", ".join(AIRPORT_SITE_KEY)
            raise ValueError(f"ClassAirspace identifiers require ({columns})")
        return identifier

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[ClassAirspace, ...]:
        """Return records matching a site key and every supported filter."""

        rows = self._table
        if identifier is not None:
            site_no, site_type_code = self._site_key(identifier)
            rows = rows[
                rows["SITE_NO"].map(self._normalized).eq(self._normalized(site_no))
                & rows["SITE_TYPE_CODE"]
                .map(self._normalized)
                .eq(self._normalized(site_type_code))
            ]
        for column, value in filters.items():
            if column not in {"airport_id", "state", "country"}:
                raise ValueError(f"Unsupported ClassAirspace filter: {column}")
            source_column = {
                "airport_id": "ARPT_ID",
                "state": "STATE_CODE",
                "country": "COUNTRY_CODE",
            }[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(
            ClassAirspace(ClassAirspaceRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object, **filters: object) -> ClassAirspace:
        """Return exactly one class-airspace record for a verified site key."""

        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


class ArtccRecord(FaaRecord):
    """Typed conveniences for one ``ARB_BASE`` row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def location_id(self) -> str | None:
        return self._text("LOCATION_ID")

    @property
    def name(self) -> str | None:
        return self._text("LOCATION_NAME")

    @property
    def center_type(self) -> str | None:
        return self._text("LOCATION_TYPE")

    @property
    def city(self) -> str | None:
        return self._text("CITY")

    @property
    def state(self) -> str | None:
        return self._text("STATE")

    @property
    def country(self) -> str | None:
        return self._text("COUNTRY_CODE")

    @property
    def latitude(self) -> str | None:
        return self._text("LAT_DECIMAL")

    @property
    def longitude(self) -> str | None:
        return self._text("LONG_DECIMAL")


class ArtccBoundary:
    """Rich view of one ARTCC boundary (a single altitude/type group).

    Wraps :class:`openNASR.arb.Boundary` directly; the ring-splitting and
    bounds logic already there is correct and is not reimplemented here.
    """

    def __init__(self, boundary: Boundary) -> None:
        self._boundary = boundary

    @property
    def lat(self) -> list[float]:
        return self._boundary.lat

    @property
    def lon(self) -> list[float]:
        return self._boundary.lon

    @property
    def latlon(self) -> list[tuple[float, float]]:
        return self._boundary.latlon

    @property
    def lonlat(self) -> list[tuple[float, float]]:
        return self._boundary.lonlat

    @property
    def getShape(self):
        return self._boundary.getShape

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self._boundary.bbox


class Artcc:
    """Rich view of an ``ARB_BASE`` row plus its ``ARB_SEG`` boundaries."""

    def __init__(
        self,
        record: ArtccRecord,
        boundaries: Mapping[str, ArtccBoundary],
    ) -> None:
        self.record = record
        self.boundaries = boundaries

    @property
    def location_id(self) -> str | None:
        return self.record.location_id

    @property
    def name(self) -> str | None:
        return self.record.name

    @property
    def high(self) -> ArtccBoundary | None:
        return self.boundaries.get("high")

    @property
    def low(self) -> ArtccBoundary | None:
        return self.boundaries.get("low")


class ArtccRepository:
    """Lookup ARTCCs by ``LOCATION_ID``, with their boundaries attached."""

    entity_type = "Artcc"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["ARB_BASE"]

    def _boundaries(self, location_id: str) -> dict[str, ArtccBoundary]:
        segments = self._nasr.get("ARB_SEG")
        if segments is None:
            return {}
        matching = segments[
            segments["LOCATION_ID"].map(self._normalized).eq(location_id)
        ]
        boundaries: dict[str, ArtccBoundary] = {}
        # Preserve FAA row order within each (ALTITUDE, TYPE) group: Boundary
        # relies on encountering a ring's points in source order to detect
        # where the ring closes, so groups must not be sorted or reordered.
        for (altitude, _boundary_type), group in matching.groupby(
            ["ALTITUDE", "TYPE"], sort=False
        ):
            key = str(altitude).strip().lower()
            boundaries[key] = ArtccBoundary(
                Boundary(group["LONG_DECIMAL"], group["LAT_DECIMAL"])
            )
        return boundaries

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[Artcc, ...]:
        """Return ARTCCs matching ``LOCATION_ID`` and every supported filter."""

        rows = self._table
        if identifier is not None:
            normalized = self._normalized(identifier)
            rows = rows[rows["LOCATION_ID"].map(self._normalized).eq(normalized)]
        for column, value in filters.items():
            if column not in {"state", "country"}:
                raise ValueError(f"Unsupported Artcc filter: {column}")
            source_column = {"state": "STATE", "country": "COUNTRY_CODE"}[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        results = []
        for row in rows.to_dict(orient="records"):
            record = ArtccRecord(row)
            results.append(
                Artcc(record, self._boundaries(self._normalized(row["LOCATION_ID"])))
            )
        return tuple(results)

    def get(self, identifier: object, **filters: object) -> Artcc:
        """Return exactly one ARTCC for a ``LOCATION_ID`` (and any filters)."""

        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


__all__ = [
    "Artcc",
    "ArtccBoundary",
    "ArtccRecord",
    "ArtccRepository",
    "ClassAirspace",
    "ClassAirspaceRepository",
]
