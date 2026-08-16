# FAA File and Type Naming Decisions

## Purpose

This file records the Python module, record-class, domain-class, repository,
and convenience-method names assigned to every FAA NASR operational CSV table.
It is a decision ledger for maintainers and coding agents, not an API reference.

All names in this file were approved by the user on 2026-08-15 and must be used
by implementation agents unless a later decision in this file supersedes them.
The status column now describes implementation origin or readiness, not naming
approval.

## Confirmed API decisions

- The primary API uses repositories:

  ```python
  nasr.airports.get("KBWI")
  nasr.airports.find(state="MD")
  ```

- Singular convenience methods are also provided:

  ```python
  nasr.airport("KBWI")
  ```

- Legacy names and constructors remain supported throughout `1.x`, with
  deprecation warnings before removal in `2.0.0`:

  ```python
  Airport("BWI", nasr)
  FIX("AABEE", nasr)
  NAVAID("ABR", nasr)
  ARB(nasr)
  ```

- Guaranteed schema support covers the current NASR schema and the FAA format
  effective September 3, 2026.
- Every operational table participates in the rich domain API. Tables without a
  reliable parent relationship receive a standalone rich object and repository;
  no relationship is inferred without support from FAA keys or documentation.
- Unexpected FAA tables, columns, missing required columns, or incompatible
  field types stop loading with a detailed schema error. Diagnostic inspection
  mode may expose the raw unfamiliar data, but normal operation never silently
  accepts schema drift.
- Data uses a two-layer representation: raw records preserve the exact FAA CSV
  text, while rich-object properties return validated Python values such as
  `date`, `int`, `float`, `bool`, enums, and geometry. Empty raw fields remain
  empty strings and become `None` only through nullable typed properties.
- Importing `openNASR` performs a metadata-only check for a newer FAA NASR
  cycle and displays a message when one is available. Import never downloads a
  cycle archive; downloading occurs only through an explicit `download_latest()`
  call.
- Import-time update-check failures remain silent and never prevent the package
  from importing. Connection and parsing details are exposed only through
  diagnostic logging or an explicitly called update-check API.
- Successful FAA cycle update checks are cached for 24 hours. Failed checks are
  not recorded as successful results and remain eligible for a later retry.
  `check_for_updates(force=True)` bypasses the cache.
- Install an `opennasr` command-line tool for cycle data management. Its initial
  commands are `check`, `download`, `list`, and `remove`; aviation data queries
  remain in the Python API.
- Version `1.0.0` requires raw loading and strict validation for every table in
  both supported FAA schemas; rich airport, runway, ILS, fix, navaid, and ARTCC
  objects; cycle caching and explicit downloads; import-time update notices;
  the CLI; automated tests; documentation; package validation; and CI. Rich
  objects for remaining families are delivered in numbered `1.x` milestones.
- All FAA table names remain uppercase when used for raw access:

  ```python
  nasr["APT_BASE"]
  nasr.table("APT_BASE")
  ```

## Supported schema inventory

Both supported FAA packages contain 63 operational CSV tables and 24
`*_CSV_DATA_STRUCTURE.csv` files, for 87 CSV files total. The NASR 10.1
transition effective September 3, 2026 changes columns but does not add or
remove tables.

The earlier planning inventory also named `AWY_ALT` and `AWY_SEG`. Neither file
exists in either official supported package. `AWY_SEG_ALT` contains the ordered
airway-segment fields and their altitude constraints, so it maps directly to
`AirwaySegmentRecord` and `Airway.segments`.

## Naming conventions

- Modules use lowercase singular domain-family names.
- Row wrappers end in `Record`.
- Rich joined objects omit the `Record` suffix.
- Repository attributes use plural nouns.
- Exact convenience lookups use singular nouns.
- FAA acronyms are expanded when the official meaning is verified and the
  expanded name remains understandable.
- The original FAA acronym remains available in table names and documentation.
- Avoid creating public classes whose only distinction is capitalization.
- Child records that make sense only within a parent include the parent domain
  in their name when needed to prevent ambiguity.

## Status values

- **Existing:** already present in some form; normalization may still be needed.
- **Proposed:** approved name for a new class or API that is not implemented yet.
- **Confirmed:** approved name that was individually selected during review.
- **Needs FAA review:** approved conservative acronym-based name; do not expand
  the acronym until official documentation confirms its meaning.

## Airport and runway files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `APT_BASE` | `airport.py` | `AirportRecord` | `Airport`; `nasr.airports`; `nasr.airport()` | Existing |
| `APT_ARS` | `airport.py` | `AirportArrestingSystemRecord` | `Airport.arresting_systems` | Confirmed |
| `APT_ATT` | `airport.py` | `AirportAttendanceRecord` | `Airport.attendance_schedules` | Proposed |
| `APT_CON` | `airport.py` | `AirportContactRecord` | `Airport.contacts` | Proposed |
| `APT_RMK` | `airport.py` | `AirportRemarkRecord` | `Airport.remarks` | Proposed |
| `APT_RWY` | `runway.py` | `RunwayRecord` | `Runway`; `Airport.runways` | Existing |
| `APT_RWY_END` | `runway.py` | `RunwayEndRecord` | `RunwayEnd`; `Runway.ends` | Existing |

## ARTCC and airspace files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `ARB_BASE` | `airspace.py` | `ArtccRecord` | `Artcc`; `nasr.artccs`; `nasr.artcc()` | Existing |
| `ARB_SEG` | `airspace.py` | `ArtccBoundarySegmentRecord` | `ArtccBoundary`; `Artcc.boundaries` | Existing |
| `CLS_ARSP` | `airspace.py` | `ClassAirspaceRecord` | `Airport.class_airspace` and `nasr.class_airspaces` | Keys verified; implementation pending |
| `MAA_BASE` | `airspace.py` | `MaaRecord` | `Maa`; `nasr.maas`; `nasr.maa()` | Needs FAA review |
| `MAA_CON` | `airspace.py` | `MaaContactRecord` | `Maa.contacts` | Needs FAA review |
| `MAA_RMK` | `airspace.py` | `MaaRemarkRecord` | `Maa.remarks` | Needs FAA review |
| `MAA_SHP` | `airspace.py` | `MaaShapePointRecord` | `Maa.geometry` | Needs FAA review |
| `PJA_BASE` | `airspace.py` | `ParachuteJumpAreaRecord` | `ParachuteJumpArea`; `nasr.parachute_jump_areas` | Proposed |
| `PJA_CON` | `airspace.py` | `ParachuteJumpAreaContactRecord` | `ParachuteJumpArea.contacts` | Proposed |

## Air traffic control and radar files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `ATC_BASE` | `atc.py` | `AtcFacilityRecord` | `AtcFacility`; `nasr.atc_facilities`; `nasr.atc_facility()` | Existing |
| `ATC_ATIS` | `atc.py` | `AtisRecord` | `AtcFacility.atis_services` | Existing |
| `ATC_RMK` | `atc.py` | `AtcRemarkRecord` | `AtcFacility.remarks` | Existing |
| `ATC_SVC` | `atc.py` | `AtcServiceRecord` | `AtcFacility.services` | Existing |
| `RDR` | `atc.py` | `RadarRecord` | `Radar`; `nasr.radars`; `nasr.radar()` | Existing |

## Weather files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `AWOS` | `weather.py` | `AutomatedWeatherStationRecord` | `AutomatedWeatherStation`; `nasr.weather_stations`; `nasr.weather_station()` | Existing |
| `WXL_BASE` | `weather.py` | `WeatherLocationRecord` | `WeatherLocation`; `nasr.weather_locations`; `nasr.weather_location()` | Existing |
| `WXL_SVC` | `weather.py` | `WeatherServiceRecord` | `WeatherLocation.services` | Existing |

## Airway files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `AWY_BASE` | `airway.py` | `AirwayRecord` | `Airway`; `nasr.airways`; `nasr.airway()` | Keys verified; rich rewrite pending |
| `AWY_SEG_ALT` | `airway.py` | `AirwaySegmentRecord` | Ordered `Airway.segments`, including altitude constraints | Keys verified; implementation pending |

## Procedure and route files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `CDR` | `routes.py` | `CodedDepartureRouteRecord` | `CodedDepartureRoute`; `nasr.coded_departure_routes` | Existing |
| `DP_BASE` | `routes.py` | `DepartureProcedureRecord` | `DepartureProcedure`; `nasr.departures`; `nasr.departure()` | Existing |
| `DP_APT` | `routes.py` | `DepartureAirportRecord` | `DepartureProcedure.airports` | Existing |
| `DP_RTE` | `routes.py` | `DepartureRouteRecord` | `DepartureProcedure.routes` | Existing |
| `PFR_BASE` | `routes.py` | `PreferredRouteRecord` | `PreferredRoute`; `nasr.preferred_routes` | Existing |
| `PFR_RMT_FMT` | `routes.py` | `PreferredRouteFormatRecord` | `PreferredRoute.formats` | Existing |
| `PFR_SEG` | `routes.py` | `PreferredRouteSegmentRecord` | `PreferredRoute.segments` | Existing |
| `STAR_BASE` | `routes.py` | `StarProcedureRecord` | `StarProcedure`; `nasr.stars`; `nasr.star()` | Proposed |
| `STAR_APT` | `routes.py` | `StarAirportRecord` | `StarProcedure.airports` | Proposed |
| `STAR_RTE` | `routes.py` | `StarRouteRecord` | `StarProcedure.routes` | Proposed |

## Fix files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `FIX_BASE` | `fix.py` | `FixRecord` | `Fix`; `nasr.fixes`; `nasr.fix()` | Existing |
| `FIX_CHRT` | `fix.py` | `FixChartRecord` | `Fix.charts` | Proposed |
| `FIX_NAV` | `fix.py` | `FixNavaidRecord` | `Fix.navaids` | Proposed |

## Communication and frequency files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `COM` | `communications.py` | `CommunicationOutletRecord` | `CommunicationOutlet`; `nasr.communication_outlets` | Existing |
| `FRQ` | `communications.py` | `FrequencyRecord` | `Frequency`; `nasr.frequencies` | Existing |

## Flight service station files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `FSS_BASE` | `fss.py` | `FlightServiceStationRecord` | `FlightServiceStation`; `nasr.flight_service_stations`; `nasr.flight_service_station()` | Existing |
| `FSS_RMK` | `fss.py` | `FlightServiceStationRemarkRecord` | `FlightServiceStation.remarks` | Existing |

## Holding pattern files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `HPF_BASE` | `holding.py` | `HoldingPatternRecord` | `HoldingPattern`; `nasr.holding_patterns` | Existing |
| `HPF_CHRT` | `holding.py` | `HoldingPatternChartRecord` | `HoldingPattern.charts` | Existing |
| `HPF_RMK` | `holding.py` | `HoldingPatternRemarkRecord` | `HoldingPattern.remarks` | Existing |
| `HPF_SPD_ALT` | `holding.py` | `HoldingPatternSpeedAltitudeRecord` | `HoldingPattern.speed_altitude_limits` | Existing |

## Instrument landing system files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `ILS_BASE` | `ils.py` | `IlsRecord` | `InstrumentLandingSystem`; `Airport.instrument_landing_systems` | Existing |
| `ILS_DME` | `ils.py` | `IlsDmeRecord` | `InstrumentLandingSystem.dme` | Existing |
| `ILS_GS` | `ils.py` | `IlsGlideSlopeRecord` | `InstrumentLandingSystem.glide_slope` | Existing |
| `ILS_MKR` | `ils.py` | `IlsMarkerRecord` | `InstrumentLandingSystem.markers` | Existing |
| `ILS_RMK` | `ils.py` | `IlsRemarkRecord` | `InstrumentLandingSystem.remarks` | Proposed |

## Location identifier file

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `LID` | `locations.py` | `LocationIdentifierRecord` | `LocationIdentifier`; `nasr.location_identifiers` | Proposed |

## Military files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `MIL_OPS` | `military.py` | `MilitaryOperationRecord` | `Airport.military_operations` | Keys verified; implementation pending |
| `MTR_BASE` | `military.py` | `MilitaryTrainingRouteRecord` | `MilitaryTrainingRoute`; `nasr.military_training_routes` | Proposed |
| `MTR_AGY` | `military.py` | `MilitaryTrainingRouteAgencyRecord` | `MilitaryTrainingRoute.agencies` | Proposed |
| `MTR_PT` | `military.py` | `MilitaryTrainingRoutePointRecord` | `MilitaryTrainingRoute.points` | Proposed |
| `MTR_SOP` | `military.py` | `MilitaryTrainingRouteProcedureRecord` | `MilitaryTrainingRoute.procedures` | Proposed |
| `MTR_TERR` | `military.py` | `MilitaryTrainingRouteTerrainRecord` | `MilitaryTrainingRoute.terrain` | Proposed |
| `MTR_WDTH` | `military.py` | `MilitaryTrainingRouteWidthRecord` | `MilitaryTrainingRoute.widths` | Proposed |

## Navaid files

| FAA CSV | Module | Proposed record class | Domain/API placement | Status |
| --- | --- | --- | --- | --- |
| `NAV_BASE` | `navaid.py` | `NavaidRecord` | `Navaid`; `nasr.navaids`; `nasr.navaid()` | Existing |
| `NAV_CKPT` | `navaid.py` | `NavaidCheckpointRecord` | `Navaid.checkpoints` | Proposed |
| `NAV_RMK` | `navaid.py` | `NavaidRemarkRecord` | `Navaid.remarks` | Proposed |

## Schema-description files

The 24 `*_CSV_DATA_STRUCTURE.csv` files do not receive separate aviation-domain
classes. They are represented through these shared types:

- `ColumnSchema`
- `TableSchema`
- `SchemaCatalog`
- `ValidationReport`

Their original tables remain available through raw access.

## Naming decision log

| Date | Scope | Decision |
| --- | --- | --- |
| 2026-08-15 | Public access pattern | Use repository-style APIs and retain singular convenience methods. |
| 2026-08-15 | Compatibility | Retain legacy names and constructors through `1.x`; remove no earlier than `2.0.0`. |
| 2026-08-15 | `APT_ARS` | Use `AirportArrestingSystemRecord`. |
| 2026-08-15 | All operational tables | Approve every module, record-class, domain-class, repository, and convenience-method name listed in this file. |
| 2026-08-15 | Domain model depth | Provide rich objects for every operational table; use standalone rich objects where no reliable aggregate relationship exists. |
| 2026-08-15 | Schema drift | Stop normal loading with a detailed coding-agent-oriented error; permit unfamiliar raw data only in explicit diagnostic inspection mode. |
| 2026-08-15 | Field values | Use a two-layer model: preserve exact CSV text in raw records and expose validated Python types through rich objects. |
| 2026-08-15 | Cycle updates | Check for a newer FAA NASR cycle during `import openNASR`, but download it only when `download_latest()` is explicitly called. |
| 2026-08-15 | Offline imports | Continue silently and never fail an import when the FAA update check cannot complete. |
| 2026-08-15 | Update-check cache | Cache successful FAA cycle checks for 24 hours, provide `force=True`, and do not cache a failed check as a successful result. |
| 2026-08-15 | Command-line API | Provide an `opennasr` CLI with `check`, `download`, `list`, and `remove` data-management commands. |
| 2026-08-15 | `1.0.0` release gate | Require complete raw/strict schema support, core rich objects, cycle management, update notices, CLI, tests, documentation, packaging, and CI; schedule remaining rich families in numbered `1.x` milestones. |
| 2026-08-16 | Supported table inventory | Use the 63 operational tables and 24 schema-description files present in both official 2026 packages; remove `AWY_ALT` and `AWY_SEG`, and model `AWY_SEG_ALT` as `AirwaySegmentRecord`. |

## Questions remaining

No naming questions remain. Future changes must update the affected table row
and add a dated entry to the naming decision log.
