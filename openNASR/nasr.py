from pathlib import Path, PurePosixPath
from datetime import date as date_cls, datetime
import tempfile
from typing import Literal
from warnings import warn
from zipfile import ZipFile
from shutil import rmtree
from pandas import DataFrame, read_csv
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
from .indexing import (
    NormalizedIndexCache,
    cached_normalized_column_index,
    normalized_index_rows,
)
from .communications import CommunicationOutletRepository, FrequencyRepository
from .routes import (
    CodedDepartureRouteRepository,
    DepartureProcedureRepository,
    PreferredRouteRepository,
    StarProcedureRepository,
)
from .military import MilitaryOperationRepository, MilitaryTrainingRouteRepository
from .cycles import CycleManager, locate_csv_source
from .duckdb_builder import (
    DuckDbBuildError,
    SOURCE_TEXT_READ_OPTIONS,
    duckdb_metadata_path,
    source_schema_fingerprint,
)
from .duckdb_metadata import read_metadata
from .duckdb_tables import DuckDbTableRepository
from .exceptions import (
    ArchiveError,
    ConfigurationError,
    CycleNotFoundError,
    SchemaMismatchError,
)
from .registry import TableRegistry
from .repository import AirportRepository, FixRepository, NavaidRepository
from .schemas import SCHEMA_SUFFIX, SchemaCatalog
from .storage import TableStore
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
        storage: Literal["csv", "duckdb"] = "csv",
    ):
        if storage not in {"csv", "duckdb"}:
            raise ConfigurationError(
                f"NASR storage must be either 'csv' or 'duckdb'; received {storage!r}."
            )
        if preloadAll:
            raise NotImplementedError("preloadAll is not yet supported")
        if update:
            # Code here will download new NASR data from FAA.
            pass
        if useDate is not None and cycle is not None and useDate != cycle:
            raise ValueError("useDate and cycle must agree when both are supplied")
        requested_cycle = cycle if cycle is not None else useDate
        self.__diagnostic = diagnostic
        self.__storage = storage
        self.__schema_fingerprint: str | None = None
        self.__legacy_indexes: NormalizedIndexCache = {}
        # Legacy ``Airport`` builds several RawDict collections from related
        # airport tables.  Keep their row mappings snapshot-scoped so repeat
        # construction does not repeatedly select and convert the same rows.
        # Constructors still make fresh ``SimpleNamespace`` instances from
        # these mappings, preserving the legacy object-identity behavior.
        self.__legacy_record_rows: dict[
            tuple[int, str, str], tuple[dict[str, object], ...]
        ] = {}
        self.setupFiles(requested_cycle, cache_dir, storage=storage)
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

    @staticmethod
    def _resolve_cycle(manager: CycleManager, useDate):
        """Return the requested (or latest) cycle with its data extracted."""

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

        if cycle.data_path is None:
            if cycle.archive_path is None:
                raise CycleNotFoundError(
                    f"No archive or extracted data found for NASR cycle "
                    f"{cycle.effective_date.isoformat()} in {manager.cache_dir}."
                )
            cycle = manager.extract_archive(cycle.archive_path)
        assert cycle.data_path is not None
        return cycle

    def _build_table_store(
        self,
        manager: CycleManager,
        cycle,
        storage: str,
        schema_files: list[str],
    ) -> tuple[TableStore, str | None]:
        """Return the loaded table store and, for DuckDB, its schema fingerprint."""

        if storage == "csv":
            read_options = (
                {"dtype": str, "keep_default_na": False, "na_filter": False}
                if schema_files
                else {}
            )
            table_repository = TableRepository(
                self.__useDateCSVFolder, read_options=read_options
            )
            return table_repository, None

        database = manager.duckdb_path(cycle.effective_date)
        if not database.is_file():
            raise DuckDbBuildError(
                "DuckDB storage was requested, but no completed artifact "
                f"exists for NASR cycle {self.__useDate}: {database}. "
                "Build it first with CycleManager.build_duckdb(...)."
            )
        metadata = read_metadata(
            duckdb_metadata_path(database),
            effective_date=cycle.effective_date,
            source_schema_fingerprint=self._source_schema_fingerprint(
                self.__useDateCSVFolder
            ),
        )
        return (
            DuckDbTableRepository(database, metadata=metadata),
            metadata.source_schema_fingerprint,
        )

    def _validate_schema_catalog(
        self, available_tables: tuple[str, ...], schema_files: list[str]
    ) -> tuple[SchemaCatalog, str, TableRegistry] | None:
        """Identify the schema and require every operational table be modeled.

        This whole-cycle check is independent of which table is requested
        first, so it runs once here, eagerly, exactly as the legacy
        eager-construction behavior did. Per-table structural validation
        (`SchemaCatalog.validate`/`ValidationReport.require_compatible`) is
        comparatively expensive (it inspects a loaded DataFrame's columns)
        and is deferred to `_load_table`, so a schema mismatch on one table
        never blocks constructing `NASR` or using a different, unrelated
        table that passes validation.
        """

        if not schema_files:
            return None
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
        return catalog, schema_id, registry

    def setupFiles(self, useDate, cache_dir=None, *, storage: str = "csv"):
        manager = CycleManager(cache_dir)
        self.__cache_dir = manager.cache_dir

        cycle = self._resolve_cycle(manager, useDate)
        self.__useDate = cycle.effective_date.isoformat()
        self.__useDateCSVFolder = self._resolve_csv_source(cycle.data_path)

        available_tables = discover_tables(self.__useDateCSVFolder)
        schema_files = [
            name for name in available_tables if name.endswith(SCHEMA_SUFFIX)
        ]

        self.__tables: TableStore
        self.__tables, duckdb_fingerprint = self._build_table_store(
            manager, cycle, storage, schema_files
        )
        if duckdb_fingerprint is not None:
            self.__schema_fingerprint = duckdb_fingerprint

        self.__schema_catalog: tuple[SchemaCatalog, str, TableRegistry] | None = (
            self._validate_schema_catalog(available_tables, schema_files)
        )

    @staticmethod
    def _source_schema_fingerprint(source: Path) -> str:
        """Fingerprint CSV table names and headers without materializing rows.

        DuckDB metadata records this same source-schema fingerprint during its
        build.  Checking it before opening the database makes an extracted
        cycle/database mismatch a typed lifecycle error rather than a silent
        fallback or a later, misleading table failure.
        """

        frames: dict[str, DataFrame] = {}
        for name in discover_tables(source):
            path = source / f"{name}.csv"
            try:
                frames[name] = read_csv(path, nrows=0, **SOURCE_TEXT_READ_OPTIONS)
            except UnicodeDecodeError:
                frames[name] = read_csv(
                    path,
                    nrows=0,
                    encoding="latin-1",
                    **SOURCE_TEXT_READ_OPTIONS,
                )
        return source_schema_fingerprint(frames)

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
            temporary = Path(tempfile.mkdtemp(prefix=".nested-", dir=source.parent))
            try:
                with ZipFile(source, "r") as archive:
                    for member in archive.infolist():
                        path = PurePosixPath(member.filename)
                        if path.is_absolute() or ".." in path.parts:
                            raise ArchiveError(
                                f"Unsafe archive member: {member.filename}"
                            )
                    archive.extractall(temporary)
                locate_csv_source(temporary)
                if extracted.exists():
                    rmtree(temporary)
                else:
                    temporary.replace(extracted)
            except Exception:
                if temporary.exists():
                    rmtree(temporary)
                raise
        return extracted

    @property
    def yearDecimal(self):
        return timestampToYearDecimal(self.__useDate)

    @property
    def storage(self) -> Literal["csv", "duckdb"]:
        """Return the explicitly selected immutable table storage backend."""

        return self.__storage

    @property
    def effective_date(self) -> str:
        """Return the exact immutable NASR cycle selected by this instance."""

        return self.__useDate

    @property
    def schema_fingerprint(self) -> str:
        """Return the source-table/header fingerprint for this exact cycle."""

        if self.__schema_fingerprint is None:
            self.__schema_fingerprint = self._source_schema_fingerprint(
                self.__useDateCSVFolder
            )
        return self.__schema_fingerprint

    @property
    def _query_table_names(self) -> tuple[str, ...]:
        """Return operational tables exposed through the bounded query API."""

        available = self.__tables.available_tables
        if self.__schema_catalog is None:
            return tuple(name for name in available if not name.endswith(SCHEMA_SUFFIX))
        _, _, registry = self.__schema_catalog
        supported = registry.supported_tables()
        return tuple(name for name in available if name in supported)

    @property
    def _query_table_store(self) -> TableStore:
        """Return the private table-store seam used by ``openNASR.query``."""

        return self.__tables

    def _query_columns(self, name: str) -> tuple[str, ...]:
        """Inspect validated queryable columns without loading DuckDB rows."""

        inspect = getattr(self.__tables, "_columns", None)
        if callable(inspect):
            columns = inspect(name)
        else:
            path = self.__useDateCSVFolder / f"{name}.csv"
            try:
                columns = tuple(
                    str(column)
                    for column in read_csv(
                        path, nrows=0, **SOURCE_TEXT_READ_OPTIONS
                    ).columns
                )
            except UnicodeDecodeError:
                columns = tuple(
                    str(column)
                    for column in read_csv(
                        path,
                        nrows=0,
                        encoding="latin-1",
                        **SOURCE_TEXT_READ_OPTIONS,
                    ).columns
                )
        self._validate_query_columns(name, columns)
        return columns

    def _query_csv_frame(self, name: str) -> DataFrame:
        """Read a CSV fallback frame as raw source text for query parity."""

        path = self.__useDateCSVFolder / f"{name}.csv"
        try:
            return read_csv(path, **SOURCE_TEXT_READ_OPTIONS)
        except UnicodeDecodeError:
            return read_csv(path, encoding="latin-1", **SOURCE_TEXT_READ_OPTIONS)

    def _validate_query_columns(self, name: str, columns: tuple[str, ...]) -> None:
        """Apply the existing catalog check without materializing DuckDB rows."""

        if self.__schema_catalog is None:
            return
        catalog, schema_id, registry = self.__schema_catalog
        if name not in registry.supported_tables():
            return
        report = catalog.validate(name, DataFrame(columns=columns), schema_id)
        if not self.__diagnostic:
            table_spec = registry.table(name)
            report.require_compatible(
                cycle=self.__useDate,
                table_spec=table_spec,
                record_class=table_spec.record_type,
            )

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

    def query_table(
        self,
        table: str,
        *,
        filters=(),
        fields=None,
        page_size: int = 100,
        cursor: str | None = None,
    ):
        """Query one immutable NASR table through the bounded read-only API.

        See :mod:`openNASR.query` for the typed filter, page, and error
        contract.  This method deliberately has no SQL argument or escape
        hatch; it delegates only validated table/field/filter requests.
        """

        from .query import query_table

        return query_table(
            self,
            table,
            filters=filters,
            fields=fields,
            page_size=page_size,
            cursor=cursor,
        )

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
        for useCol in ["ARPT_ID", "ICAO_ID"]:
            rows = self._legacy_normalized_rows("APT_BASE", useCol, airport)
            if not rows.empty:
                isAirportBool = True
                airportIDCol = useCol
                ARPT_ID = rows["ARPT_ID"].tolist()[0]
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
        return not self._legacy_normalized_rows("FIX_BASE", "FIX_ID", fix).empty

    @staticmethod
    def _legacy_normalized(value: object) -> str:
        return str(value).strip().upper()

    def _legacy_normalized_rows(
        self, table: str, column: str, value: object
    ) -> DataFrame:
        """Return one legacy lookup group from this NASR snapshot's cache."""

        frame = self[table]
        index = cached_normalized_column_index(
            self.__legacy_indexes, frame, column, self._legacy_normalized
        )
        return normalized_index_rows(frame, index, value, self._legacy_normalized)

    def _legacy_normalized_records(
        self, table: str, column: str, value: object
    ) -> tuple[dict[str, object], ...]:
        """Return cached row mappings for a legacy compatibility lookup.

        This intentionally layers on ``_legacy_normalized_rows`` so the
        source-order, case-insensitive matching rule remains centralized.
        It is only consumed by legacy Airport assembly; callers must make
        fresh raw objects from the mappings rather than sharing them.
        """

        frame = self[table]
        key = (id(frame), column, self._legacy_normalized(value))
        records = self.__legacy_record_rows.get(key)
        if records is None:
            records = tuple(
                self._legacy_normalized_rows(table, column, value).to_dict(
                    orient="records"
                )
            )
            self.__legacy_record_rows[key] = records
        return records

    def isNavaid(self, nav: str):
        return not self._legacy_normalized_rows("NAV_BASE", "NAV_ID", nav).empty

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
