# openNASR

openNASR is a local Python library for loading, querying, relating, and plotting
Federal Aviation Administration (FAA) National Airspace System Resources
(NASR) subscription data.

## What is NASR data?

The FAA publishes NASR aeronautical reference data on a 28-day effective
cycle. A subscription contains many related tables describing airports,
runways, runway ends, instrument landing systems, fixes, navigation aids,
airways, procedures, airspace, air traffic facilities, weather facilities, and
other components of the United States National Airspace System.

Current and historical subscription information is available from the
[FAA 28-Day NASR Subscription page](https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/).
Each cached cycle remains separate in openNASR so an explicitly selected
effective date is never silently replaced with another cycle.

## Why use a Python library?

The FAA distribution consists of numerous CSV tables connected by identifiers
and composite keys. openNASR provides lazy pandas table access plus typed
records, repositories, ordered child collections, and resolved relationships.
This makes the source data easier to explore without hiding or rewriting its
original FAA values.

Important uses include:

- plotting airport layouts from runway and runway-end coordinates;
- inspecting and plotting Instrument Landing System (ILS), glide-slope (GS),
  DME, and marker information associated with runways;
- constructing and plotting ARTCC and other airspace boundaries together with
  airports, fixes, navigation aids, and intersecting airways;
- processing historical flight-plan route fields against the exact NASR cycle
  that was effective at the time, then plotting the resolved route; and
- analyzing the original cycle tables directly with pandas when a higher-level
  domain object is not needed.

Historical route processing is source-backed analysis, not operational flight
planning or clearance validation. Always use current official FAA sources for
navigation and safety-critical decisions.

## Major data classes

openNASR organizes related FAA tables into domain records and repositories.
These are the major data areas available through the library; follow a link for
source-table details, lookup keys, relationships, examples, and the generated
Python API.

### Cycles and airports

| Data area | Information represented |
| --- | --- |
| [NASR cycle](types/nasr-cycle.md) | One exact FAA subscription effective date, its locally cached files, lazy tables, and domain repositories. |
| [Airports](types/airport.md) | Airport identity, name, location, elevation, status, ownership and operational fields, plus relationships to runways, airspace, ILS, and military operations. |
| [Runways](types/runway.md) | Landing-surface identifiers, dimensions, surface and status, together with runway-end coordinates, elevations, declared distances, and related fields. |
| [Instrument landing systems](types/ils.md) | Runway-associated ILS base records and their localizer, glide-slope (GS), DME, and marker components. |
| [Fixes](types/fix.md) | Named fixes with coordinates, state, country, ARTCC, and other FAA-published attributes. |
| [Navigation aids](types/navaid.md) | VOR, VORTAC, NDB, and other navaid identities, types, frequencies, coordinates, and ARTCC associations. |

### Airspace and activity areas

| Data area | Information represented |
| --- | --- |
| [ARTCCs](types/artcc.md) | Air Route Traffic Control Center identities and ordered high- and low-altitude boundary geometry. |
| [Class airspace](types/class-airspace.md) | Airport-linked controlled-airspace records identified by the FAA's complete site key. |
| [Miscellaneous Activity Areas](types/maa.md) | Aerobatic, glider, space-launch, ultralight, unmanned-aircraft, and other published activity areas, including contacts and remarks. |
| [Parachute Jump Areas](types/parachute-jump-area.md) | Published jump-area center points, radii, operating information, contacts, and optional airport relationships. |

### Routes, procedures, and flight plans

| Data area | Information represented |
| --- | --- |
| [Airways](types/airways.md) | Airway identities, FAA-ordered route segments, fixes or navaids, and segment altitude constraints. |
| [Holding patterns](types/holding-pattern.md) | Holding-pattern identity and geometry, chart references, remarks, speed and altitude restrictions, and associated fixes. |
| [Arrivals](types/arrivals.md) | Standard Terminal Arrival Routes (STARs), airport associations, transitions, and ordered route points. |
| [Departures](types/departures.md) | Coded departure routes and departure procedures, including airport associations, transitions, and ordered route points. |
| [Preferred routes](types/preferred-route.md) | FAA preferred-route identities, route-format variants, and ordered segments between origin and destination areas. |
| [Flight planning](types/flightplan.md) | Resolution of domestic FAA route text into ordered airport, fix, navaid, airway, departure, arrival, and transition coordinates for analysis and plotting. |

### Aviation and military services

| Data area | Information represented |
| --- | --- |
| [Aviation services](types/aviation-services.md) | ATC facilities, radar sites, communication outlets, frequency assignments, automated weather stations, Flight Service Stations, and FAA location identifiers. |
| [Military data](types/military-data.md) | Airport-linked military operations and military training routes with their agencies, route points, schedules, and related published records. |

## Documentation

```{toctree}
:maxdepth: 2
:caption: Documentation

using-the-library
types/index
csv-tables/index
reference/index
```

```{toctree}
:maxdepth: 1
:caption: Examples

examples/index
examples/plotting-airport
examples/plotting-ils
examples/plotting-artcc
examples/flight-plan-path
```

```{toctree}
:maxdepth: 1
:caption: Benchmarks

route_path_baseline_2026-05-14
speedup_benchmark_2026-05-14
DUCKDB_BENCHMARK_REPORT_TEMPLATE
SPEEDUP_BENCHMARK_REPORT_TEMPLATE
```
