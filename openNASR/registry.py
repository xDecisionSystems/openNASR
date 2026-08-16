"""Schema-version-aware registry for supported FAA NASR tables."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .exceptions import SchemaMismatchError, TableNotFoundError
from .airspace import ClassAirspaceRecord
from .airway import AirwayRecord, AirwaySegmentRecord
from .arrivals import StarAirportRecord, StarProcedureRecord, StarRouteRecord
from .atc import (
    AtcFacilityRecord,
    AtcRemarkRecord,
    AtcServiceRecord,
    AtisRecord,
    RadarRecord,
)
from .communications import CommunicationOutletRecord, FrequencyRecord
from .departure import (
    CodedDepartureRouteRecord,
    DepartureAirportRecord,
    DepartureProcedureRecord,
    DepartureRouteRecord,
    PreferredRouteFormatRecord,
    PreferredRouteRecord,
    PreferredRouteSegmentRecord,
)
from .fss import FlightServiceStationRecord, FlightServiceStationRemarkRecord
from .holding import (
    HoldingPatternChartRecord,
    HoldingPatternRecord,
    HoldingPatternRemarkRecord,
    HoldingPatternSpeedAltitudeRecord,
)
from .locations import LocationIdentifierRecord
from .military import MilitaryOperationRecord
from .records import FaaRecord, FixRecord, NavaidRecord
from .weather import (
    AutomatedWeatherStationRecord,
    WeatherLocationRecord,
    WeatherServiceRecord,
)
from .schemas import SchemaCatalog


AIRPORT_SITE_KEY = ("SITE_NO", "SITE_TYPE_CODE")
AIRPORT_LINKED_TABLES = frozenset({"CLS_ARSP", "MIL_OPS"})
AIRWAY_KEY = ("REGULATORY", "AWY_LOCATION", "AWY_ID")
AIRWAY_SEGMENT_KEY = (*AIRWAY_KEY, "POINT_SEQ")
AIRWAY_TABLES = frozenset({"AWY_BASE", "AWY_SEG_ALT"})
HOLDING_PATTERN_KEY = ("HP_NAME", "HP_NO", "STATE_CODE", "COUNTRY_CODE")
HOLDING_PATTERN_TABLES = frozenset({"HPF_BASE", "HPF_CHRT", "HPF_RMK", "HPF_SPD_ALT"})
FIX_KEY = ("FIX_ID", "ICAO_REGION_CODE", "STATE_CODE", "COUNTRY_CODE")
NAVAID_KEY = ("NAV_ID", "NAV_TYPE", "CITY", "STATE_CODE", "COUNTRY_CODE")
AIRWAY_FIX_KEY = ("FROM_POINT", "ICAO_REGION_CODE", "STATE_CODE", "COUNTRY_CODE")
AIRWAY_NAVAID_KEY = (
    "FROM_POINT",
    "FROM_PT_TYPE",
    "NAV_CITY",
    "STATE_CODE",
    "COUNTRY_CODE",
)
COMMUNICATION_NAVAID_KEY = (
    "NAV_ID",
    "NAV_TYPE",
    "CITY",
    "STATE_CODE",
    "COUNTRY_CODE",
)
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
CDR_KEY = ("RCode",)
DEPARTURE_KEY = ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE")
DEPARTURE_AIRPORT_KEY = (
    *DEPARTURE_KEY,
    "BODY_NAME",
    "BODY_SEQ",
    "ARPT_ID",
    "RWY_END_ID",
)
DEPARTURE_ROUTE_KEY = (
    *DEPARTURE_KEY,
    "ROUTE_PORTION_TYPE",
    "ROUTE_NAME",
    "BODY_SEQ",
    "TRANSITION_COMPUTER_CODE",
    "POINT_SEQ",
)
DEPARTURE_ROUTE_ORDER = (
    "BODY_SEQ",
    "ROUTE_PORTION_TYPE",
    "ROUTE_NAME",
    "TRANSITION_COMPUTER_CODE",
    "POINT_SEQ",
)
PREFERRED_ROUTE_KEY = ("ORIGIN_ID", "DSTN_ID", "PFR_TYPE_CODE", "ROUTE_NO")
PREFERRED_ROUTE_FORMAT_KEY = ("Orig", "Dest", "Type", "Seq")
PREFERRED_ROUTE_SEGMENT_KEY = (*PREFERRED_ROUTE_KEY, "SEGMENT_SEQ")
STAR_KEY = ("STAR_COMPUTER_CODE", "ARTCC")
STAR_AIRPORT_KEY = (
    *STAR_KEY,
    "BODY_NAME",
    "BODY_SEQ",
    "ARPT_ID",
    "RWY_END_ID",
)
STAR_ROUTE_KEY = (
    *STAR_KEY,
    "ROUTE_PORTION_TYPE",
    "ROUTE_NAME",
    "BODY_SEQ",
    "TRANSITION_COMPUTER_CODE",
    "POINT_SEQ",
)
STAR_ROUTE_ORDER = (
    "BODY_SEQ",
    "ROUTE_PORTION_TYPE",
    "ROUTE_NAME",
    "TRANSITION_COMPUTER_CODE",
    "POINT_SEQ",
)
PROCEDURE_ROUTE_TABLES = frozenset(
    {
        "CDR",
        "DP_BASE",
        "DP_APT",
        "DP_RTE",
        "PFR_BASE",
        "PFR_RMT_FMT",
        "PFR_SEG",
        "STAR_BASE",
        "STAR_APT",
        "STAR_RTE",
    }
)
ATC_KEY = (
    "SITE_NO",
    "SITE_TYPE_CODE",
    "FACILITY_TYPE",
    "STATE_CODE",
    "FACILITY_ID",
    "CITY",
    "COUNTRY_CODE",
)
WEATHER_LOCATION_KEY = ("WEA_ID", "CITY", "STATE_CODE", "COUNTRY_CODE")
FSS_KEY = ("FSS_ID", "NAME", "CITY", "STATE_CODE", "COUNTRY_CODE")
FACILITY_TABLES = frozenset(
    {
        "ATC_BASE",
        "ATC_ATIS",
        "ATC_RMK",
        "ATC_SVC",
        "RDR",
        "AWOS",
        "WXL_BASE",
        "WXL_SVC",
        "FSS_BASE",
        "FSS_RMK",
        "LID",
    }
)
RICH_RECORD_TYPES: Mapping[str, type[FaaRecord]] = {
    "ATC_BASE": AtcFacilityRecord,
    "ATC_ATIS": AtisRecord,
    "ATC_RMK": AtcRemarkRecord,
    "ATC_SVC": AtcServiceRecord,
    "RDR": RadarRecord,
    "AWOS": AutomatedWeatherStationRecord,
    "WXL_BASE": WeatherLocationRecord,
    "WXL_SVC": WeatherServiceRecord,
    "FSS_BASE": FlightServiceStationRecord,
    "FSS_RMK": FlightServiceStationRemarkRecord,
    "LID": LocationIdentifierRecord,
    "CDR": CodedDepartureRouteRecord,
    "DP_BASE": DepartureProcedureRecord,
    "DP_APT": DepartureAirportRecord,
    "DP_RTE": DepartureRouteRecord,
    "PFR_BASE": PreferredRouteRecord,
    "PFR_RMT_FMT": PreferredRouteFormatRecord,
    "PFR_SEG": PreferredRouteSegmentRecord,
    "STAR_BASE": StarProcedureRecord,
    "STAR_APT": StarAirportRecord,
    "STAR_RTE": StarRouteRecord,
    "AWY_BASE": AirwayRecord,
    "AWY_SEG_ALT": AirwaySegmentRecord,
    "CLS_ARSP": ClassAirspaceRecord,
    "MIL_OPS": MilitaryOperationRecord,
    "HPF_BASE": HoldingPatternRecord,
    "HPF_CHRT": HoldingPatternChartRecord,
    "HPF_RMK": HoldingPatternRemarkRecord,
    "HPF_SPD_ALT": HoldingPatternSpeedAltitudeRecord,
    "COM": CommunicationOutletRecord,
    "FRQ": FrequencyRecord,
    "FIX_BASE": FixRecord,
    "NAV_BASE": NavaidRecord,
}


@dataclass(frozen=True)
class IndexSpec:
    """Columns used by a named lookup index."""

    name: str
    columns: tuple[str, ...]
    unique: bool = False


@dataclass(frozen=True)
class RelationshipSpec:
    """Verified columns connecting one table to another."""

    name: str
    target_table: str
    local_columns: tuple[str, ...]
    target_columns: tuple[str, ...]


@dataclass(frozen=True)
class TableVariantSpec:
    """Metadata for one table in one supported schema generation."""

    schema_id: str
    identity_key: tuple[str, ...] | None = None
    indexes: tuple[IndexSpec, ...] = ()
    order_by: tuple[str, ...] = ()
    relationships: tuple[RelationshipSpec, ...] = ()
    required_columns: frozenset[str] = frozenset()
    optional: bool = False


@dataclass(frozen=True)
class TableSpec:
    """Record type and schema variants for one operational FAA table."""

    name: str
    record_type: type[FaaRecord]
    variants: tuple[TableVariantSpec, ...]


class TableRegistry:
    """Registry of every supported operational FAA table."""

    def __init__(
        self,
        specs: Iterable[TableSpec] | None = None,
        *,
        catalog: SchemaCatalog | None = None,
    ) -> None:
        self.catalog = catalog or SchemaCatalog()
        if specs is None:
            specs = self._build_specs()
        self._specs = {spec.name: spec for spec in specs}

    def _build_specs(self) -> tuple[TableSpec, ...]:
        manifests = {
            schema_id: self.catalog.manifest(schema_id)
            for schema_id in self.catalog.SUPPORTED_SCHEMA_IDS
        }
        table_names = sorted(
            set().union(*(manifest["tables"] for manifest in manifests.values()))
        )
        specs = []
        for table_name in table_names:
            variants = []
            for schema_id, manifest in manifests.items():
                if table_name not in manifest["tables"]:
                    continue
                schema = self.catalog.table(table_name, schema_id)
                identity_key: tuple[str, ...] | None = None
                indexes: tuple[IndexSpec, ...] = ()
                order_by: tuple[str, ...] = ()
                relationships: tuple[RelationshipSpec, ...] = ()
                if table_name in AIRPORT_LINKED_TABLES:
                    identity_key = AIRPORT_SITE_KEY
                    indexes = (
                        IndexSpec("site", AIRPORT_SITE_KEY, unique=True),
                        IndexSpec("airport_id", ("ARPT_ID",), unique=False),
                    )
                    relationships = (
                        RelationshipSpec(
                            "airport",
                            "APT_BASE",
                            AIRPORT_SITE_KEY,
                            AIRPORT_SITE_KEY,
                        ),
                    )
                elif table_name == "AWY_BASE":
                    identity_key = AIRWAY_KEY
                    indexes = (IndexSpec("airway", AIRWAY_KEY, unique=True),)
                    relationships = (
                        RelationshipSpec(
                            "segments",
                            "AWY_SEG_ALT",
                            AIRWAY_KEY,
                            AIRWAY_KEY,
                        ),
                    )
                elif table_name == "AWY_SEG_ALT":
                    identity_key = AIRWAY_SEGMENT_KEY
                    indexes = (
                        IndexSpec("segment", AIRWAY_SEGMENT_KEY, unique=True),
                        IndexSpec("airway", AIRWAY_KEY, unique=False),
                    )
                    order_by = ("POINT_SEQ",)
                    relationships = (
                        RelationshipSpec(
                            "airway",
                            "AWY_BASE",
                            AIRWAY_KEY,
                            AIRWAY_KEY,
                        ),
                        RelationshipSpec("fix", "FIX_BASE", AIRWAY_FIX_KEY, FIX_KEY),
                        RelationshipSpec(
                            "navaid", "NAV_BASE", AIRWAY_NAVAID_KEY, NAVAID_KEY
                        ),
                    )
                elif table_name == "FIX_BASE":
                    identity_key = FIX_KEY
                    indexes = (
                        IndexSpec("fix", FIX_KEY, unique=True),
                        IndexSpec("identifier", ("FIX_ID",), unique=False),
                    )
                    relationships = (
                        RelationshipSpec(
                            "airway_segments",
                            "AWY_SEG_ALT",
                            FIX_KEY,
                            AIRWAY_FIX_KEY,
                        ),
                        RelationshipSpec(
                            "holding_patterns",
                            "HPF_BASE",
                            FIX_KEY,
                            FIX_KEY,
                        ),
                    )
                elif table_name == "NAV_BASE":
                    identity_key = NAVAID_KEY
                    indexes = (
                        IndexSpec("navaid", NAVAID_KEY, unique=True),
                        IndexSpec("identifier", ("NAV_ID",), unique=False),
                    )
                    relationships = (
                        RelationshipSpec(
                            "airway_segments",
                            "AWY_SEG_ALT",
                            NAVAID_KEY,
                            AIRWAY_NAVAID_KEY,
                        ),
                        RelationshipSpec(
                            "communication_outlets",
                            "COM",
                            NAVAID_KEY,
                            COMMUNICATION_NAVAID_KEY,
                        ),
                    )
                elif table_name == "HPF_BASE":
                    identity_key = HOLDING_PATTERN_KEY
                    indexes = (
                        IndexSpec("holding_pattern", HOLDING_PATTERN_KEY, unique=True),
                    )
                    relationships = (
                        RelationshipSpec(
                            "charts",
                            "HPF_CHRT",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                        RelationshipSpec(
                            "remarks",
                            "HPF_RMK",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                        RelationshipSpec(
                            "speed_altitude_limits",
                            "HPF_SPD_ALT",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                        RelationshipSpec("fix", "FIX_BASE", FIX_KEY, FIX_KEY),
                    )
                elif table_name == "HPF_CHRT":
                    identity_key = (*HOLDING_PATTERN_KEY, "CHARTING_TYPE_DESC")
                    indexes = (IndexSpec("holding_pattern", HOLDING_PATTERN_KEY),)
                    relationships = (
                        RelationshipSpec(
                            "holding_pattern",
                            "HPF_BASE",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                    )
                elif table_name == "HPF_RMK":
                    identity_key = (
                        *HOLDING_PATTERN_KEY,
                        "TAB_NAME",
                        "REF_COL_NAME",
                        "REF_COL_SEQ_NO",
                    )
                    indexes = (IndexSpec("holding_pattern", HOLDING_PATTERN_KEY),)
                    order_by = ("TAB_NAME", "REF_COL_NAME", "REF_COL_SEQ_NO")
                    relationships = (
                        RelationshipSpec(
                            "holding_pattern",
                            "HPF_BASE",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                    )
                elif table_name == "HPF_SPD_ALT":
                    identity_key = (*HOLDING_PATTERN_KEY, "SPEED_RANGE", "ALTITUDE")
                    indexes = (IndexSpec("holding_pattern", HOLDING_PATTERN_KEY),)
                    relationships = (
                        RelationshipSpec(
                            "holding_pattern",
                            "HPF_BASE",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                    )
                elif table_name == "COM":
                    indexes = (
                        IndexSpec(
                            "communication_outlet", ("COMM_LOC_ID",), unique=False
                        ),
                        IndexSpec("navaid", COMMUNICATION_NAVAID_KEY, unique=False),
                    )
                    relationships = (
                        RelationshipSpec(
                            "navaid",
                            "NAV_BASE",
                            COMMUNICATION_NAVAID_KEY,
                            NAVAID_KEY,
                        ),
                    )
                elif table_name == "FRQ":
                    identity_key = FREQUENCY_KEY
                    indexes = (
                        IndexSpec("frequency", FREQUENCY_KEY, unique=True),
                        IndexSpec(
                            "serviced_facility", SERVICED_FACILITY_KEY, unique=False
                        ),
                    )
                elif table_name == "CDR":
                    identity_key = CDR_KEY
                    indexes = (IndexSpec("route_code", CDR_KEY, unique=True),)
                elif table_name == "DP_BASE":
                    identity_key = DEPARTURE_KEY
                    indexes = (
                        IndexSpec("departure", DEPARTURE_KEY, unique=True),
                        IndexSpec("computer_code", ("DP_COMPUTER_CODE",)),
                    )
                    relationships = (
                        RelationshipSpec(
                            "airports", "DP_APT", DEPARTURE_KEY, DEPARTURE_KEY
                        ),
                        RelationshipSpec(
                            "routes", "DP_RTE", DEPARTURE_KEY, DEPARTURE_KEY
                        ),
                    )
                elif table_name == "DP_APT":
                    identity_key = DEPARTURE_AIRPORT_KEY
                    indexes = (
                        IndexSpec("departure", DEPARTURE_KEY),
                        IndexSpec("airport_id", ("ARPT_ID",)),
                    )
                    order_by = ("BODY_SEQ", "ARPT_ID", "RWY_END_ID")
                    relationships = (
                        RelationshipSpec(
                            "departure", "DP_BASE", DEPARTURE_KEY, DEPARTURE_KEY
                        ),
                    )
                elif table_name == "DP_RTE":
                    identity_key = DEPARTURE_ROUTE_KEY
                    indexes = (IndexSpec("departure", DEPARTURE_KEY),)
                    order_by = DEPARTURE_ROUTE_ORDER
                    relationships = (
                        RelationshipSpec(
                            "departure", "DP_BASE", DEPARTURE_KEY, DEPARTURE_KEY
                        ),
                    )
                elif table_name == "PFR_BASE":
                    identity_key = PREFERRED_ROUTE_KEY
                    indexes = (
                        IndexSpec("preferred_route", PREFERRED_ROUTE_KEY, unique=True),
                    )
                    relationships = (
                        RelationshipSpec(
                            "formats",
                            "PFR_RMT_FMT",
                            PREFERRED_ROUTE_KEY,
                            PREFERRED_ROUTE_FORMAT_KEY,
                        ),
                        RelationshipSpec(
                            "segments",
                            "PFR_SEG",
                            PREFERRED_ROUTE_KEY,
                            PREFERRED_ROUTE_KEY,
                        ),
                    )
                elif table_name == "PFR_RMT_FMT":
                    identity_key = PREFERRED_ROUTE_FORMAT_KEY
                    indexes = (
                        IndexSpec(
                            "preferred_route", PREFERRED_ROUTE_FORMAT_KEY, unique=True
                        ),
                    )
                    relationships = (
                        RelationshipSpec(
                            "preferred_route",
                            "PFR_BASE",
                            PREFERRED_ROUTE_FORMAT_KEY,
                            PREFERRED_ROUTE_KEY,
                        ),
                    )
                elif table_name == "PFR_SEG":
                    identity_key = PREFERRED_ROUTE_SEGMENT_KEY
                    indexes = (IndexSpec("preferred_route", PREFERRED_ROUTE_KEY),)
                    order_by = ("SEGMENT_SEQ",)
                    relationships = (
                        RelationshipSpec(
                            "preferred_route",
                            "PFR_BASE",
                            PREFERRED_ROUTE_KEY,
                            PREFERRED_ROUTE_KEY,
                        ),
                    )
                elif table_name == "STAR_BASE":
                    identity_key = STAR_KEY
                    indexes = (
                        IndexSpec("star", STAR_KEY, unique=True),
                        IndexSpec("computer_code", ("STAR_COMPUTER_CODE",)),
                    )
                    relationships = (
                        RelationshipSpec("airports", "STAR_APT", STAR_KEY, STAR_KEY),
                        RelationshipSpec("routes", "STAR_RTE", STAR_KEY, STAR_KEY),
                    )
                elif table_name == "STAR_APT":
                    identity_key = STAR_AIRPORT_KEY
                    indexes = (
                        IndexSpec("star", STAR_KEY),
                        IndexSpec("airport_id", ("ARPT_ID",)),
                    )
                    order_by = ("BODY_SEQ", "ARPT_ID", "RWY_END_ID")
                    relationships = (
                        RelationshipSpec("star", "STAR_BASE", STAR_KEY, STAR_KEY),
                    )
                elif table_name == "STAR_RTE":
                    identity_key = STAR_ROUTE_KEY
                    indexes = (IndexSpec("star", STAR_KEY),)
                    order_by = STAR_ROUTE_ORDER
                    relationships = (
                        RelationshipSpec("star", "STAR_BASE", STAR_KEY, STAR_KEY),
                    )
                elif table_name == "ATC_BASE":
                    identity_key = ATC_KEY
                    indexes = (IndexSpec("facility", ATC_KEY, unique=True),)
                    relationships = tuple(
                        RelationshipSpec(name, target, ATC_KEY, ATC_KEY)
                        for name, target in (
                            ("atis_services", "ATC_ATIS"),
                            ("remarks", "ATC_RMK"),
                            ("services", "ATC_SVC"),
                        )
                    )
                elif table_name in {"ATC_ATIS", "ATC_RMK", "ATC_SVC"}:
                    suffix = {
                        "ATC_ATIS": ("ATIS_NO",),
                        "ATC_RMK": (
                            "LEGACY_ELEMENT_NUMBER",
                            "TAB_NAME",
                            "REF_COL_NAME",
                            "REMARK_NO",
                        ),
                        "ATC_SVC": ("CTL_SVC",),
                    }[table_name]
                    identity_key = (*ATC_KEY, *suffix)
                    indexes = (IndexSpec("facility", ATC_KEY),)
                    relationships = (
                        RelationshipSpec("facility", "ATC_BASE", ATC_KEY, ATC_KEY),
                    )
                    if table_name == "ATC_RMK":
                        order_by = ("REMARK_NO",)
                elif table_name == "RDR":
                    identity_key = (
                        "FACILITY_ID",
                        "FACILITY_TYPE",
                        "STATE_CODE",
                        "COUNTRY_CODE",
                        "RADAR_TYPE",
                        "RADAR_NO",
                    )
                elif table_name == "AWOS":
                    identity_key = (
                        "ASOS_AWOS_ID",
                        "ASOS_AWOS_TYPE",
                        "STATE_CODE",
                        "CITY",
                        "COUNTRY_CODE",
                    )
                elif table_name == "WXL_BASE":
                    identity_key = WEATHER_LOCATION_KEY
                    relationships = (
                        RelationshipSpec(
                            "services",
                            "WXL_SVC",
                            WEATHER_LOCATION_KEY,
                            WEATHER_LOCATION_KEY,
                        ),
                    )
                elif table_name == "WXL_SVC":
                    identity_key = (*WEATHER_LOCATION_KEY, "WEA_SVC_TYPE_CODE")
                    indexes = (IndexSpec("weather_location", WEATHER_LOCATION_KEY),)
                    relationships = (
                        RelationshipSpec(
                            "weather_location",
                            "WXL_BASE",
                            WEATHER_LOCATION_KEY,
                            WEATHER_LOCATION_KEY,
                        ),
                    )
                elif table_name == "FSS_BASE":
                    identity_key = FSS_KEY
                    relationships = (
                        RelationshipSpec("remarks", "FSS_RMK", FSS_KEY, FSS_KEY),
                    )
                elif table_name == "FSS_RMK":
                    identity_key = (*FSS_KEY, "REF_COL_NAME", "REF_COL_SEQ_NO")
                    indexes = (IndexSpec("flight_service_station", FSS_KEY),)
                    order_by = ("REF_COL_NAME", "REF_COL_SEQ_NO")
                    relationships = (
                        RelationshipSpec(
                            "flight_service_station", "FSS_BASE", FSS_KEY, FSS_KEY
                        ),
                    )
                elif table_name == "LID":
                    identity_key = (
                        "COUNTRY_CODE",
                        "LOC_ID",
                        "REGION_CODE",
                        "STATE",
                        "CITY",
                        "LID_GROUP",
                        "FAC_TYPE",
                    )
                variants.append(
                    TableVariantSpec(
                        schema_id=schema_id,
                        identity_key=identity_key,
                        indexes=indexes,
                        order_by=order_by,
                        relationships=relationships,
                        required_columns=frozenset(
                            column.name for column in schema.columns
                        ),
                    )
                )
            specs.append(
                TableSpec(
                    name=table_name,
                    record_type=RICH_RECORD_TYPES.get(table_name, FaaRecord),
                    variants=tuple(variants),
                )
            )
        return tuple(specs)

    def table(self, name: str) -> TableSpec:
        try:
            return self._specs[name.upper()]
        except KeyError as error:
            raise TableNotFoundError(f"Table {name!r} is not registered") from error

    def spec(self, name: str, schema_id: str) -> TableVariantSpec:
        table = self.table(name)
        for variant in table.variants:
            if variant.schema_id == schema_id:
                return variant
        raise TableNotFoundError(
            f"Table {name!r} has no variant for schema {schema_id!r}"
        )

    def supported_tables(self) -> frozenset[str]:
        return frozenset(self._specs)

    def unmodeled_tables(self, available: Iterable[str | Path]) -> frozenset[str]:
        names = {Path(item).stem.upper() for item in available}
        return frozenset(names - self.supported_tables())

    def require_modeled(
        self,
        available: Iterable[str | Path],
        *,
        cycle: str | Path | None = None,
        diagnostic: bool = False,
    ) -> frozenset[str]:
        """Reject unknown operational tables unless diagnostic mode is explicit."""

        unmodeled = self.unmodeled_tables(available)
        if unmodeled and not diagnostic:
            instructions = (
                "Update openNASR/schemas.py, openNASR/registry.py, the relevant "
                "domain module and record class, fixtures, the coverage manifest, "
                "and PLAN.md."
            )
            raise SchemaMismatchError(
                f"Unmodeled NASR tables in {cycle or 'unknown cycle'}: "
                f"{sorted(unmodeled)}. {instructions}",
                cycle=str(cycle) if cycle is not None else None,
                unmodeled_tables=tuple(sorted(unmodeled)),
                instructions=instructions,
            )
        return unmodeled


__all__ = [
    "AIRPORT_LINKED_TABLES",
    "AIRPORT_SITE_KEY",
    "AIRWAY_KEY",
    "AIRWAY_SEGMENT_KEY",
    "AIRWAY_TABLES",
    "AIRWAY_FIX_KEY",
    "AIRWAY_NAVAID_KEY",
    "ATC_KEY",
    "CDR_KEY",
    "COMMUNICATION_NAVAID_KEY",
    "FIX_KEY",
    "FACILITY_TABLES",
    "FSS_KEY",
    "DEPARTURE_AIRPORT_KEY",
    "DEPARTURE_KEY",
    "DEPARTURE_ROUTE_KEY",
    "DEPARTURE_ROUTE_ORDER",
    "HOLDING_PATTERN_KEY",
    "HOLDING_PATTERN_TABLES",
    "FREQUENCY_KEY",
    "NAVAID_KEY",
    "PREFERRED_ROUTE_FORMAT_KEY",
    "PREFERRED_ROUTE_KEY",
    "PREFERRED_ROUTE_SEGMENT_KEY",
    "PROCEDURE_ROUTE_TABLES",
    "SERVICED_FACILITY_KEY",
    "STAR_AIRPORT_KEY",
    "STAR_KEY",
    "STAR_ROUTE_KEY",
    "STAR_ROUTE_ORDER",
    "WEATHER_LOCATION_KEY",
    "IndexSpec",
    "RICH_RECORD_TYPES",
    "RelationshipSpec",
    "TableRegistry",
    "TableSpec",
    "TableVariantSpec",
]
