"""Rich objects for FAA airspace tables: airport-linked class airspace and
ARTCC boundaries."""

from __future__ import annotations

from collections.abc import Mapping

from pandas import DataFrame

from .arb import Boundary
from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FaaRecord, dms_coordinate, integer, nullable_text

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


class MaaRecord(FaaRecord):
    """Typed conveniences for one ``MAA_BASE`` row.

    ``MAA`` is the FAA's "Miscellaneous Activity Area" family (aerobatic
    practice, glider, hang glider, space launch, ultralight, and unmanned
    aircraft areas) — confirmed from the FAA's own ``MAA DATA LAYOUT.pdf``
    (PLAN.md Milestone 12, task 12.1). It is unrelated to military airspace.
    """

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def maa_id(self) -> str | None:
        return self._text("MAA_ID")

    @property
    def type_name(self) -> str | None:
        return self._text("MAA_TYPE_NAME")

    @property
    def name(self) -> str | None:
        return self._text("MAA_NAME")

    @property
    def city(self) -> str | None:
        return self._text("CITY")

    @property
    def state(self) -> str | None:
        return self._text("STATE_CODE")

    @property
    def max_altitude(self) -> str | None:
        return self._text("MAX_ALT")

    @property
    def min_altitude(self) -> str | None:
        return self._text("MIN_ALT")

    @property
    def radius(self) -> str | None:
        return self._text("MAA_RADIUS")

    @property
    def description(self) -> str | None:
        return self._text("DESCRIPTION")

    @property
    def use(self) -> str | None:
        return self._text("MAA_USE")

    @property
    def time_of_use(self) -> str | None:
        return self._text("TIME_OF_USE")

    @property
    def user_group_name(self) -> str | None:
        return self._text("USER_GROUP_NAME")

    @property
    def airport_ids(self) -> tuple[str, ...]:
        """FAA landing-facility identifiers associated with this area."""

        raw = self._text("ARPT_IDS")
        return tuple(raw.split()) if raw else ()


class MaaContactRecord(FaaRecord):
    """Typed conveniences for an ordered ``MAA_CON`` frequency-contact row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def sequence(self) -> int | None:
        value = self._text("FREQ_SEQ")
        return None if value is None else integer(value)

    @property
    def facility_id(self) -> str | None:
        return self._text("FAC_ID")

    @property
    def facility_name(self) -> str | None:
        return self._text("FAC_NAME")

    @property
    def commercial_frequency(self) -> str | None:
        return self._text("COMMERCIAL_FREQ")

    @property
    def military_frequency(self) -> str | None:
        return self._text("MIL_FREQ")


class MaaRemarkRecord(FaaRecord):
    """Typed conveniences for an ordered ``MAA_RMK`` remark row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def table_name(self) -> str | None:
        return self._text("TAB_NAME")

    @property
    def reference_column(self) -> str | None:
        return self._text("REF_COL_NAME")

    @property
    def sequence(self) -> int | None:
        value = self._text("REF_COL_SEQ_NO")
        return None if value is None else integer(value)

    @property
    def remark(self) -> str | None:
        return self._text("REMARK")


class MaaShapePointRecord(FaaRecord):
    """Typed conveniences for an ordered ``MAA_SHP`` polygon-point row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def sequence(self) -> int | None:
        value = self._text("POINT_SEQ")
        return None if value is None else integer(value)

    @property
    def latitude(self) -> float | None:
        value = self._text("LATITUDE")
        return None if value is None else dms_coordinate(value)

    @property
    def longitude(self) -> float | None:
        value = self._text("LONGITUDE")
        return None if value is None else dms_coordinate(value)


class Maa:
    """One Miscellaneous Activity Area with its contacts, remarks, and shape."""

    def __init__(
        self,
        record: MaaRecord,
        *,
        contacts: tuple[MaaContactRecord, ...],
        remarks: tuple[MaaRemarkRecord, ...],
        shape_points: tuple[MaaShapePointRecord, ...],
    ) -> None:
        self.record = record
        self.contacts = contacts
        self.remarks = remarks
        self.shape_points = shape_points

    @property
    def maa_id(self) -> str | None:
        return self.record.maa_id

    @property
    def name(self) -> str | None:
        return self.record.name

    @property
    def geometry(self):
        """A Shapely polygon built from the ordered ``MAA_SHP`` points.

        Returns ``None`` when the area has no published shape (some
        ``MAA_BASE`` rows describe only a center point and radius).
        ``MAA_SHP`` rings are not explicitly closed in FAA source data
        (unlike ``ARB_SEG``), so the first point is appended to close the
        ring before building the polygon.
        """

        if not self.shape_points:
            return None
        points = [
            (point.longitude, point.latitude)
            for point in self.shape_points
            if point.longitude is not None and point.latitude is not None
        ]
        if not points:
            return None
        if points[0] != points[-1]:
            points = [*points, points[0]]
        lons, lats = zip(*points)
        return Boundary(lons, lats).getShape


class MaaRepository:
    """Lookup Miscellaneous Activity Areas by ``MAA_ID``."""

    entity_type = "Maa"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["MAA_BASE"]

    def _matching(self, frame: DataFrame, maa_id: str) -> DataFrame:
        return frame[frame["MAA_ID"].map(self._normalized).eq(maa_id)]

    @staticmethod
    def _contact_order(row: dict[str, object]) -> int:
        sequence = row.get("FREQ_SEQ")
        return int(str(sequence)) if sequence not in (None, "") else -1

    @staticmethod
    def _remark_order(row: dict[str, object]) -> tuple[str, str, int]:
        sequence = row.get("REF_COL_SEQ_NO")
        return (
            str(row.get("TAB_NAME", "")),
            str(row.get("REF_COL_NAME", "")),
            int(str(sequence)) if sequence not in (None, "") else -1,
        )

    @staticmethod
    def _point_order(row: dict[str, object]) -> int:
        sequence = row.get("POINT_SEQ")
        return int(str(sequence)) if sequence not in (None, "") else -1

    def _maa(self, row: dict[str, object]) -> Maa:
        maa_id = self._normalized(row["MAA_ID"])
        contacts = sorted(
            self._matching(self._nasr["MAA_CON"], maa_id).to_dict(orient="records"),
            key=self._contact_order,
        )
        remarks = sorted(
            self._matching(self._nasr["MAA_RMK"], maa_id).to_dict(orient="records"),
            key=self._remark_order,
        )
        shape_points = sorted(
            self._matching(self._nasr["MAA_SHP"], maa_id).to_dict(orient="records"),
            key=self._point_order,
        )
        return Maa(
            MaaRecord(row),
            contacts=tuple(MaaContactRecord(item) for item in contacts),
            remarks=tuple(MaaRemarkRecord(item) for item in remarks),
            shape_points=tuple(MaaShapePointRecord(item) for item in shape_points),
        )

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[Maa, ...]:
        """Return areas matching ``MAA_ID`` and every supported filter."""

        rows = self._table
        if identifier is not None:
            normalized = self._normalized(identifier)
            rows = rows[rows["MAA_ID"].map(self._normalized).eq(normalized)]
        for column, value in filters.items():
            if column not in {"state", "type_name"}:
                raise ValueError(f"Unsupported Maa filter: {column}")
            source_column = {"state": "STATE_CODE", "type_name": "MAA_TYPE_NAME"}[
                column
            ]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(self._maa(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object, **filters: object) -> Maa:
        """Return exactly one area for a ``MAA_ID`` (and any filters)."""

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
    "Maa",
    "MaaContactRecord",
    "MaaRecord",
    "MaaRemarkRecord",
    "MaaRepository",
    "MaaShapePointRecord",
]
