from pathlib import Path
from datetime import date as date_cls, datetime
from warnings import warn
from zipfile import ZipFile
from pandas import DataFrame
from .arb import ARB
from .airspace import (
    ArtccRepository,
    ClassAirspaceRepository,
    MaaRepository,
    ParachuteJumpAreaRepository,
)
from .atc import AtcFacilityRepository, RadarRepository
from .weather import AutomatedWeatherStationRepository, WeatherLocationRepository
from .fss import FlightServiceStationRepository
from .locations import LocationIdentifierRepository
from .airway import AirwayRepository
from .holding import HoldingPatternRepository
from .communications import CommunicationOutletRepository, FrequencyRepository
from .routes import (
    CodedDepartureRouteRepository,
    DepartureProcedureRepository,
    PreferredRouteRepository,
    StarProcedureRepository,
)
from .military import MilitaryOperationRepository, MilitaryTrainingRouteRepository
from .cycles import CycleManager, locate_csv_source
from .exceptions import CycleNotFoundError, SchemaMismatchError
from .registry import TableRegistry
from .repository import AirportRepository, FixRepository, NavaidRepository
from .schemas import SCHEMA_SUFFIX, SchemaCatalog
from .tables import TableRepository, discover_tables
import calendar
# from .airport import AIRPORT


def timestampToYearDecimal(useDate):
    # Convert the timestamp to a datetime object
    dt = datetime.strptime(useDate, "%Y-%m-%d")
    # Extract the year.
    year = dt.year

    # Calculate the total number of days in the year
    if calendar.isleap(year):
        days_in_year = 366
    else:
        days_in_year = 365
    # Calculate the day of the year
    day_of_year = (dt - datetime(year, 1, 1)).days + 1

    # Calculate the year in decimal format
    year_decimal = year + (day_of_year - 1) / days_in_year
    return year_decimal


class NASR(dict):
    def __init__(
        self,
        useDate=None,
        update=False,
        preloadAll=False,
        diagnostic=False,
        *,
        cycle=None,
        cache_dir=None,
    ):
        if preloadAll:
            raise NotImplementedError("preloadAll is not yet supported")
        if update:
            # Code here will download new NASR data from FAA.
            pass
        if useDate is not None and cycle is not None and useDate != cycle:
            raise ValueError("useDate and cycle must agree when both are supplied")
        requested_cycle = cycle if cycle is not None else useDate
        self.__diagnostic = diagnostic
        self.setupFiles(requested_cycle, cache_dir)
        self.class_airspaces = ClassAirspaceRepository(self)
        self.artccs = ArtccRepository(self)
        self.maas = MaaRepository(self)
        self.parachute_jump_areas = ParachuteJumpAreaRepository(self)
        self.atc_facilities = AtcFacilityRepository(self)
        self.radars = RadarRepository(self)
        self.weather_stations = AutomatedWeatherStationRepository(self)
        self.weather_locations = WeatherLocationRepository(self)
        self.flight_service_stations = FlightServiceStationRepository(self)
        self.location_identifiers = LocationIdentifierRepository(self)
        self.airways = AirwayRepository(self)
        self.holding_patterns = HoldingPatternRepository(self)
        self.communication_outlets = CommunicationOutletRepository(self)
        self.frequencies = FrequencyRepository(self)
        self.coded_departure_routes = CodedDepartureRouteRepository(self)
        self.departures = DepartureProcedureRepository(self)
        self.preferred_routes = PreferredRouteRepository(self)
        self.stars = StarProcedureRepository(self)
        self.military_operations = MilitaryOperationRepository(self)
        self.military_training_routes = MilitaryTrainingRouteRepository(self)
        self.airports = AirportRepository(self)
        self.fixes = FixRepository(self)
        self.navaids = NavaidRepository(self)

    def setupFiles(self, useDate, cache_dir=None):
        manager = CycleManager(cache_dir)
        self.__cache_dir = manager.cache_dir

        if useDate is None:
            cycle = manager.latest()
        else:
            try:
                requested_date = date_cls.fromisoformat(useDate)
            except ValueError as error:
                raise CycleNotFoundError(
                    f"Invalid NASR cycle date {useDate!r}; expected YYYY-MM-DD."
                ) from error
            found = manager.get(requested_date)
            if found is None:
                raise CycleNotFoundError(
                    f"No NASR cycle found for requested date {useDate} in "
                    f"{manager.cache_dir}. Import or download a matching "
                    "28DaySubscription_Effective_YYYY-MM-DD.zip archive first."
                )
            cycle = found

        self.__useDate = cycle.effective_date.isoformat()

        if cycle.data_path is None:
            if cycle.archive_path is None:
                raise CycleNotFoundError(
                    f"No archive or extracted data found for NASR cycle "
                    f"{self.__useDate} in {manager.cache_dir}."
                )
            cycle = manager.extract_archive(cycle.archive_path)

        self.__useDateCSVFolder = self._resolve_csv_source(cycle.data_path)
        available_tables = discover_tables(self.__useDateCSVFolder)
        schema_files = [
            name for name in available_tables if name.endswith(SCHEMA_SUFFIX)
        ]
        read_options = (
            {"dtype": str, "keep_default_na": False, "na_filter": False}
            if schema_files
            else {}
        )
        self.__tables = TableRepository(
            self.__useDateCSVFolder, read_options=read_options
        )

        # Schema identification and the "every discovered table is modeled"
        # check are whole-cycle questions independent of which table is
        # requested first, so they run once here, eagerly, exactly as the
        # legacy eager-construction behavior did. Per-table structural
        # validation (`SchemaCatalog.validate`/`ValidationReport
        # .require_compatible`) is comparatively expensive (it inspects a
        # loaded DataFrame's columns) and is deferred to `_load_table`, so a
        # schema mismatch on one table never blocks constructing `NASR` or
        # using a different, unrelated table that passes validation.
        if schema_files:
            catalog = SchemaCatalog()
            schema_id = catalog.identify_schema(self.__useDateCSVFolder)
            registry = TableRegistry(catalog=catalog)
            operational_names = [
                name for name in available_tables if not name.endswith(SCHEMA_SUFFIX)
            ]
            registry.require_modeled(
                operational_names,
                cycle=self.__useDate,
                diagnostic=self.__diagnostic,
            )
            self.__schema_catalog: tuple[SchemaCatalog, str, TableRegistry] | None = (
                catalog,
                schema_id,
                registry,
            )
        else:
            self.__schema_catalog = None

    @staticmethod
    def _resolve_csv_source(data_path: Path) -> Path:
        """Return a directory of CSVs, extracting one more nested archive if needed."""

        source = locate_csv_source(data_path)
        if source.is_dir():
            return source
        extracted = source.parent / source.stem
        if not extracted.exists():
            warn(
                "NASR archive is being decompressed: %s" % source,
                stacklevel=3,
            )
            with ZipFile(source, "r") as zObject:
                zObject.extractall(extracted)
        return extracted

    @property
    def yearDecimal(self):
        return timestampToYearDecimal(self.__useDate)

    def _load_table(self, name: str) -> DataFrame:
        """Load one table and, if the cycle has a known schema, validate it.

        Only this table's own structural validation happens here; whole-cycle
        schema identification and the modeled-table check already happened
        once, eagerly, in :meth:`setupFiles`.
        """

        frame = self.__tables.load(name)
        if self.__schema_catalog is not None and not name.endswith(SCHEMA_SUFFIX):
            catalog, schema_id, registry = self.__schema_catalog
            if name in registry.supported_tables():
                report = catalog.validate(name, frame, schema_id)
                if not self.__diagnostic:
                    table_spec = registry.table(name)
                    report.require_compatible(
                        cycle=self.__useDate,
                        table_spec=table_spec,
                        record_class=table_spec.record_type,
                    )
        if name == "APT_BASE" and "ARPT_ID" not in frame.columns:
            raise SchemaMismatchError(
                "APT_BASE is missing required identifier column ARPT_ID",
                cycle=self.__useDate,
                table="APT_BASE",
                missing_columns=("ARPT_ID",),
            )
        return frame

    def table(self, name: str, *, copy: bool = False) -> DataFrame:
        """Return a lazily loaded, validated, per-table-cached DataFrame.

        Storage lives entirely in the wrapped :class:`TableRepository`; this
        instance's own ``dict`` body is never populated. Every ``Mapping``
        method below delegates so ``nasr["APT_BASE"]``, ``"APT_BASE" in
        nasr``, ``nasr.keys()``, and similar legacy usage keep working.

        Validation (schema drift, the ``APT_BASE`` identifier check) runs
        only the first time a table is loaded; :class:`TableRepository`
        itself caches the DataFrame, so a validated table is never
        re-validated on subsequent access.
        """

        already_loaded = self.__tables.is_loaded(name)
        frame = self.__tables.load(name) if already_loaded else self._load_table(name)
        return frame.copy(deep=True) if copy else frame

    def is_loaded(self, name: str) -> bool:
        return self.__tables.is_loaded(name)

    def __getitem__(self, name):
        return self.table(name)

    def __contains__(self, name):
        try:
            return name.strip().upper() in self.__tables.available_tables
        except AttributeError:
            return False

    def keys(self):
        return self.__tables.available_tables

    def __iter__(self):
        return iter(self.__tables.available_tables)

    def __len__(self):
        return len(self.__tables.available_tables)

    def get(self, name, default=None):
        try:
            return self[name]
        except SchemaMismatchError:
            raise
        except Exception:
            return default

    def isAirport(self, airport: str, forceFAA: bool = True):
        """Return whether an airport exists and its matched identifier details.

        Returns ``(exists, matched_column, faa_identifier)``. When
        ``forceFAA`` is true, related-table callers receive ``ARPT_ID`` as the
        matched column and the FAA identifier as the lookup value. FAA and
        ICAO identifiers are matched case-insensitively, consistent with the
        modern ``nasr.airport()``/``nasr.airports`` facade.
        """
        isAirportBool = False
        airportIDCol = None
        ARPT_ID = None
        normalized_airport = str(airport).strip().upper()
        for useCol in ["ARPT_ID", "ICAO_ID"]:
            column = self["APT_BASE"][useCol]
            matches = column.map(lambda value: str(value).strip().upper()) == (
                normalized_airport
            )
            if any(matches):
                isAirportBool = True
                airportIDCol = useCol
                ARPT_ID = self["APT_BASE"][matches]["ARPT_ID"].tolist()[0]
                break
        if forceFAA:
            airportIDCol = "ARPT_ID"
        return isAirportBool, airportIDCol, ARPT_ID

    def airport(self, identifier: str):
        """Return the airport selected by :attr:`airports`."""
        return self.airports.get(identifier)

    def fix(self, identifier: str):
        """Return the fix selected by :attr:`fixes`."""
        return self.fixes.get(identifier)

    def navaid(self, identifier: str, **filters):
        """Return the navaid selected by :attr:`navaids`."""
        return self.navaids.get(identifier, **filters)

    def artcc(self, identifier: str, **filters):
        """Return the ARTCC selected by :attr:`artccs`."""
        return self.artccs.get(identifier, **filters)

    def maa(self, identifier: str, **filters):
        """Return the Miscellaneous Activity Area selected by :attr:`maas`."""
        return self.maas.get(identifier, **filters)

    def parachute_jump_area(self, identifier: str, **filters):
        """Return the area selected by :attr:`parachute_jump_areas`."""
        return self.parachute_jump_areas.get(identifier, **filters)

    def military_training_route(self, identifier: tuple[str, str]):
        """Return the route selected by its ``(ROUTE_TYPE_CODE, ROUTE_ID)`` key."""
        return self.military_training_routes.get(identifier)

    def airway(self, identifier: tuple[str, str, str]):
        """Return the airway selected by its complete FAA composite key."""
        return self.airways.get(identifier)

    def holding_pattern(self, identifier: tuple[str, str, str | None, str]):
        """Return the holding pattern selected by its complete FAA key."""
        return self.holding_patterns.get(identifier)

    def communication_outlet(self, identifier: str):
        """Return the communication outlet selected by its FAA identifier."""
        return self.communication_outlets.get(identifier)

    def frequency(self, identifier: tuple[object, ...]):
        """Return the frequency selected by its complete FAA composite key."""
        return self.frequencies.get(identifier)

    def coded_departure_route(self, identifier: str):
        """Return the coded departure route selected by FAA route code."""
        return self.coded_departure_routes.get(identifier)

    def departure(self, identifier: tuple[object, ...]):
        """Return a departure procedure selected by its complete FAA key."""
        return self.departures.get(identifier)

    def preferred_route(self, identifier: tuple[object, ...]):
        return self.preferred_routes.get(identifier)

    def star(self, identifier: tuple[object, ...]):
        return self.stars.get(identifier)

    def atc_facility(self, identifier: tuple[object, ...]):
        return self.atc_facilities.get(identifier)

    def radar(self, identifier: tuple[object, ...]):
        return self.radars.get(identifier)

    def weather_station(self, identifier: tuple[object, ...]):
        return self.weather_stations.get(identifier)

    def weather_location(self, identifier: tuple[object, ...]):
        return self.weather_locations.get(identifier)

    def flight_service_station(self, identifier: tuple[object, ...]):
        return self.flight_service_stations.get(identifier)

    def location_identifier(self, identifier: tuple[object, ...]):
        return self.location_identifiers.get(identifier)

    def isAirway(self, airway: str):
        return airway in self["AWY_BASE"]["AWY_ID"].to_list()

    def isDeparture(self, departure: str):
        return (
            departure
            in self["DP_BASE"]["DP_COMPUTER_CODE"]
            .apply(lambda dpCode: dpCode.split(".")[0])
            .to_list()
        )

    def isFix(self, fix: str):
        normalized_fix = str(fix).strip().upper()
        return (
            normalized_fix
            in (
                self["FIX_BASE"]["FIX_ID"].map(lambda value: str(value).strip().upper())
            ).to_list()
        )

    def isNavaid(self, nav: str):
        normalized_nav = str(nav).strip().upper()
        return (
            normalized_nav
            in (
                self["NAV_BASE"]["NAV_ID"].map(lambda value: str(value).strip().upper())
            ).to_list()
        )

    def isStar(self, star: str):
        return (
            star
            in self["STAR_BASE"]["STAR_COMPUTER_CODE"]
            .apply(lambda starCode: starCode.split(".")[1])
            .to_list()
        )

    def loadARTCC(self):
        self.artcc = ARB(self)

    # def loadAirports(self):
    #     self.airports = AIRPORT(self['ARB_BASE'],self['ARB_SEG'],arbType='ARTCC')


# myNASR=NASR()
