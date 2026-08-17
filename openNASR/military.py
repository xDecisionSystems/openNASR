"""Rich objects for FAA military-operation and military-training-route tables."""

from __future__ import annotations

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .indexing import NormalizedIndexCache, normalized_indexed_rows
from .records import FaaRecord, integer, nullable_text

AIRPORT_SITE_KEY = ("SITE_NO", "SITE_TYPE_CODE")
MTR_KEY = ("ROUTE_TYPE_CODE", "ROUTE_ID")


class MilitaryOperationRecord(FaaRecord):
    """Typed conveniences for one airport-linked military-operation row."""

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
    def operating_code(self) -> str | None:
        return self._text("MIL_OPS_OPER_CODE")

    @property
    def call_sign(self) -> str | None:
        return self._text("MIL_OPS_CALL")

    @property
    def operating_hours(self) -> str | None:
        return self._text("MIL_OPS_HRS")


class MilitaryOperation:
    """Rich view of a ``MIL_OPS`` row linked to one airport site."""

    def __init__(self, record: MilitaryOperationRecord) -> None:
        self.record = record

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        return self.record.airport_site_key

    @property
    def airport_id(self) -> str | None:
        return self.record.airport_id

    @property
    def operating_code(self) -> str | None:
        return self.record.operating_code

    @property
    def call_sign(self) -> str | None:
        return self.record.call_sign

    @property
    def operating_hours(self) -> str | None:
        return self.record.operating_hours


class MilitaryOperationRepository:
    """Lookup military operations by their verified airport-site key."""

    entity_type = "MilitaryOperation"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["MIL_OPS"]

    def _site_key(self, identifier: object) -> tuple[object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            AIRPORT_SITE_KEY
        ):
            columns = ", ".join(AIRPORT_SITE_KEY)
            raise ValueError(f"MilitaryOperation identifiers require ({columns})")
        return identifier

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[MilitaryOperation, ...]:
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
                raise ValueError(f"Unsupported MilitaryOperation filter: {column}")
            source_column = {
                "airport_id": "ARPT_ID",
                "state": "STATE_CODE",
                "country": "COUNTRY_CODE",
            }[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(
            MilitaryOperation(MilitaryOperationRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object, **filters: object) -> MilitaryOperation:
        """Return exactly one military-operation record for a verified site key."""

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


class MilitaryTrainingRouteRecord(FaaRecord):
    """Typed conveniences for an ``MTR_BASE`` row.

    ``ARTCC`` is listed as "common to all MTR files" in the FAA's own
    ``MTR DATA LAYOUT.pdf`` and present as a column on every ``MTR_*`` table,
    but it is a space-separated list of ARTCC idents the route traverses
    (e.g. ``"ZJX ZTL"``), not part of the identity key -- verified against
    the real archive and confirmed by ``MTR_CSV_DATA_STRUCTURE.csv``
    declaring it ``Nullable`` while ``ROUTE_TYPE_CODE``/``ROUTE_ID`` are not
    (PLAN.md Milestone 12 task 12.2).
    """

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def route_type_code(self) -> str | None:
        return self._text("ROUTE_TYPE_CODE")

    @property
    def route_id(self) -> str | None:
        return self._text("ROUTE_ID")

    @property
    def route_key(self) -> tuple[str, str] | None:
        route_type_code = self.route_type_code
        route_id = self.route_id
        if route_type_code is None or route_id is None:
            return None
        return route_type_code, route_id

    @property
    def artccs(self) -> tuple[str, ...]:
        """ARTCC idents the route traverses (descriptive, not a key)."""

        raw = self._text("ARTCC")
        return tuple(raw.split()) if raw else ()

    @property
    def flight_service_stations(self) -> tuple[str, ...]:
        raw = self._text("FSS")
        return tuple(raw.split()) if raw else ()

    @property
    def time_of_use(self) -> str | None:
        return self._text("TIME_OF_USE")


class MilitaryTrainingRouteAgencyRecord(FaaRecord):
    """Typed conveniences for an ``MTR_AGY`` agency row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def agency_type(self) -> str | None:
        return self._text("AGENCY_TYPE")

    @property
    def agency_name(self) -> str | None:
        return self._text("AGENCY_NAME")

    @property
    def station(self) -> str | None:
        return self._text("STATION")

    @property
    def city(self) -> str | None:
        return self._text("CITY")

    @property
    def state(self) -> str | None:
        return self._text("STATE_CODE")

    @property
    def commercial_phone(self) -> str | None:
        return self._text("COMMERCIAL_NO")

    @property
    def dsn_phone(self) -> str | None:
        return self._text("DSN_NO")

    @property
    def hours(self) -> str | None:
        return self._text("HOURS")


class MilitaryTrainingRoutePointRecord(FaaRecord):
    """Typed conveniences for an ``MTR_PT`` ordered route-point row.

    The FAA's own ``MTR DATA LAYOUT.pdf`` documents ``MTR_PT`` as the one
    ``MTR_*`` table where the "ordered by" list and the actual unique key
    diverge: it is *ordered* by ``ROUTE_PT_SEQ`` (points "in order adapted
    for given MTR", sequenced in multiples of ten) but its *identity key*
    uses ``ROUTE_PT_ID`` instead, per an explicit footnote (PLAN.md
    Milestone 12 task 12.2). :attr:`identifier` therefore uses
    ``ROUTE_PT_ID``, while :attr:`sequence` is used only for display order.
    """

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def identifier(self) -> str | None:
        return self._text("ROUTE_PT_ID")

    @property
    def sequence(self) -> int | None:
        value = self._text("ROUTE_PT_SEQ")
        return None if value is None else integer(value)

    @property
    def next_point_id(self) -> str | None:
        return self._text("NEXT_ROUTE_PT_ID")

    @property
    def segment_text(self) -> str | None:
        return self._text("SEGMENT_TEXT")

    @property
    def latitude(self) -> float | None:
        value = self._text("LAT_DECIMAL")
        return None if value is None else float(value)

    @property
    def longitude(self) -> float | None:
        value = self._text("LONG_DECIMAL")
        return None if value is None else float(value)

    @property
    def navaid_id(self) -> str | None:
        return self._text("NAV_ID")


class MilitaryTrainingRouteProcedureRecord(FaaRecord):
    """Typed conveniences for an ``MTR_SOP`` standard-operating-procedure row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def sequence(self) -> int | None:
        value = self._text("SOP_SEQ_NO")
        return None if value is None else integer(value)

    @property
    def text(self) -> str | None:
        return self._text("SOP_TEXT")


class MilitaryTrainingRouteTerrainRecord(FaaRecord):
    """Typed conveniences for an ``MTR_TERR`` terrain-following-operations row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def sequence(self) -> int | None:
        value = self._text("TERRAIN_SEQ_NO")
        return None if value is None else integer(value)

    @property
    def text(self) -> str | None:
        return self._text("TERRAIN_TEXT")


class MilitaryTrainingRouteWidthRecord(FaaRecord):
    """Typed conveniences for an ``MTR_WDTH`` route-width row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def sequence(self) -> int | None:
        value = self._text("WIDTH_SEQ_NO")
        return None if value is None else integer(value)

    @property
    def text(self) -> str | None:
        return self._text("WIDTH_TEXT")


class MilitaryTrainingRoute:
    """One military training route with its agencies, points, and text."""

    def __init__(
        self,
        record: MilitaryTrainingRouteRecord,
        *,
        agencies: tuple[MilitaryTrainingRouteAgencyRecord, ...],
        points: tuple[MilitaryTrainingRoutePointRecord, ...],
        procedures: tuple[MilitaryTrainingRouteProcedureRecord, ...],
        terrain: tuple[MilitaryTrainingRouteTerrainRecord, ...],
        widths: tuple[MilitaryTrainingRouteWidthRecord, ...],
    ) -> None:
        self.record = record
        self.agencies = agencies
        self.points = points
        self.procedures = procedures
        self.terrain = terrain
        self.widths = widths

    @property
    def route_key(self) -> tuple[str, str] | None:
        return self.record.route_key


class MilitaryTrainingRouteRepository:
    """Lookup military training routes by ``(ROUTE_TYPE_CODE, ROUTE_ID)``."""

    entity_type = "MilitaryTrainingRoute"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr
        self._indexes: NormalizedIndexCache = {}

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["MTR_BASE"]

    def _key(self, identifier: object) -> tuple[object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(MTR_KEY):
            columns = ", ".join(MTR_KEY)
            raise ValueError(f"MilitaryTrainingRoute identifiers require ({columns})")
        return identifier

    def _matching(self, frame: DataFrame, key: tuple[object, object]) -> DataFrame:
        return normalized_indexed_rows(
            self._indexes, frame, zip(MTR_KEY, key), self._normalized
        )

    @staticmethod
    def _sequence_order(column: str):
        def order(row: dict[str, object]) -> int:
            sequence = row.get(column)
            return int(str(sequence)) if sequence not in (None, "") else -1

        return order

    def _route(self, row: dict[str, object]) -> MilitaryTrainingRoute:
        key = (row["ROUTE_TYPE_CODE"], row["ROUTE_ID"])
        agencies = sorted(
            self._matching(self._nasr["MTR_AGY"], key).to_dict(orient="records"),
            key=lambda item: str(item.get("AGENCY_TYPE", "")),
        )
        points = sorted(
            self._matching(self._nasr["MTR_PT"], key).to_dict(orient="records"),
            key=self._sequence_order("ROUTE_PT_SEQ"),
        )
        procedures = sorted(
            self._matching(self._nasr["MTR_SOP"], key).to_dict(orient="records"),
            key=self._sequence_order("SOP_SEQ_NO"),
        )
        terrain = sorted(
            self._matching(self._nasr["MTR_TERR"], key).to_dict(orient="records"),
            key=self._sequence_order("TERRAIN_SEQ_NO"),
        )
        widths = sorted(
            self._matching(self._nasr["MTR_WDTH"], key).to_dict(orient="records"),
            key=self._sequence_order("WIDTH_SEQ_NO"),
        )
        return MilitaryTrainingRoute(
            MilitaryTrainingRouteRecord(row),
            agencies=tuple(
                MilitaryTrainingRouteAgencyRecord(item) for item in agencies
            ),
            points=tuple(MilitaryTrainingRoutePointRecord(item) for item in points),
            procedures=tuple(
                MilitaryTrainingRouteProcedureRecord(item) for item in procedures
            ),
            terrain=tuple(MilitaryTrainingRouteTerrainRecord(item) for item in terrain),
            widths=tuple(MilitaryTrainingRouteWidthRecord(item) for item in widths),
        )

    def find(
        self, identifier: object | None = None
    ) -> tuple[MilitaryTrainingRoute, ...]:
        """Return routes matching ``(ROUTE_TYPE_CODE, ROUTE_ID)``."""

        rows = self._table
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(self._route(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object) -> MilitaryTrainingRoute:
        """Return exactly one route for ``(ROUTE_TYPE_CODE, ROUTE_ID)``."""

        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type, identifier=identifier, candidates=records
            )
        return records[0]


__all__ = [
    "MilitaryOperation",
    "MilitaryOperationRepository",
    "MilitaryTrainingRoute",
    "MilitaryTrainingRouteAgencyRecord",
    "MilitaryTrainingRoutePointRecord",
    "MilitaryTrainingRouteProcedureRecord",
    "MilitaryTrainingRouteRecord",
    "MilitaryTrainingRouteRepository",
    "MilitaryTrainingRouteTerrainRecord",
    "MilitaryTrainingRouteWidthRecord",
]
