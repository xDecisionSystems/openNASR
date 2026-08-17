# openNASR

`openNASR` is a Python library for loading and working with the Federal Aviation
Administration (FAA) National Airspace System Resources (NASR) 28-day
subscription data.

The project turns the FAA CSV tables into Python objects for airports, runways,
instrument landing systems, fixes, navigation aids, and ARTCC boundaries. The
underlying tables remain available as pandas `DataFrame` objects when direct
access is more convenient.

> **Development status:** This project is under active development. The public
> API and local data layout may change. Automatic NASR downloads are not yet
> implemented.

## Features

- Load the CSV tables from an FAA NASR subscription cycle.
- Select a locally available cycle by effective date.
- Access any loaded table by its FAA table name, such as `APT_BASE` or
  `NAV_BASE`.
- Look up airports using FAA or ICAO identifiers.
- Inspect airport runways, runway ends, ILS, glide-slope, DME, and marker data.
- Inspect airport-linked class airspace and military-operation data through the
  typed repository facade.
- Inspect airways, holding patterns, communication outlets, and frequencies
  through typed repositories with composite-key relationships.
- Inspect ATC facilities, radar, weather stations and locations, flight service
  stations, and location identifiers through typed FAA-keyed repositories.
- Look up fixes and navigation aids.
- Build ARTCC boundary polygons with Shapely.
- Inspect miscellaneous activity areas, parachute jump areas, and military
  training routes through typed repositories.
- Convert latitude/longitude coordinates to local nautical-mile coordinates.
- Plot airport runways and ILS information with Matplotlib.

See the [API reference](docs/API.md) for public classes and methods.
See [MIGRATION.md](MIGRATION.md) when updating code from legacy constructors.
See [CHANGELOG.md](CHANGELOG.md) for release history.
See [CONTRIBUTING.md](CONTRIBUTING.md) for development and verification instructions.

## Requirements

- Python 3.10 or newer
- pandas
- NumPy
- Shapely
- Matplotlib (optional; required only for plotting)

## Installation

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/xDecisionSystems/openNASR.git
cd openNASR
python -m pip install -e .
```

Editable installation is recommended while the package is in development.

### Optional DuckDB support

DuckDB is an optional local-storage acceleration feature. Install it only when
you need the DuckDB backend; the normal installation does not install DuckDB:

```bash
python -m pip install -e ".[duckdb]"
```

## NASR data setup

FAA NASR data is published on a 28-day cycle. Download a full subscription ZIP
from the [FAA 28-Day NASR Subscription page](https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/).

Place the downloaded archive in:

```text
openNASR/data/zip/
```

The expected filename format is:

```text
28DaySubscription_Effective_YYYY-MM-DD.zip
```

For example:

```text
openNASR/data/zip/28DaySubscription_Effective_2024-06-13.zip
```

When `NASR` opens a cycle for the first time, it extracts the archive beneath:

```text
openNASR/data/uncompressed/
```

NASR archives and extracted data can be large and should not be committed to
the repository.

`CycleManager` stores downloaded archives and extracted cycles beneath its
cache directory. Cache location precedence is:

1. an explicit `cache_dir` argument;
2. the `OPENNASR_CACHE_DIR` environment variable; or
3. the platform-specific user cache directory selected by `platformdirs`.

For example, `CycleManager(cache_dir="/data/nasr")` uses `/data/nasr`
regardless of environment settings. Within that directory, archives are kept
under `archives/` and extracted cycles under `cycles/`.

### Optional DuckDB cycle artifacts

DuckDB is an explicit, opt-in derivative of an extracted cycle. It is not
created while importing or loading CSV data. After installing the optional
extra, build one artifact by exact effective date:

```bash
python -m pip install -e ".[duckdb]"
opennasr build-duckdb 2024-06-13
opennasr build-duckdb latest
opennasr list --storage
```

The artifact and its provenance sidecar are stored beside that cycle:

```text
<cache>/cycles/2024-06-13/nasr.duckdb
<cache>/cycles/2024-06-13/nasr.duckdb.json
```

Use `NASR(cycle="2024-06-13", storage="duckdb")` to open an already-built
artifact. DuckDB mode never silently selects a neighboring cycle, downloads a
cycle, or rebuilds a missing artifact. The CSV-backed default remains
`storage="csv"`. Building a database requires additional disk space roughly
equal to the materialized tables; rebuilding replaces only that cycle's
derivative. Remove it selectively with
`CycleManager().remove("2024-06-13", archive=False, extracted=False, duckdb=True)`.
Removing the DuckDB artifact does not remove the archive or extracted CSVs.

The sidecar records the exact effective date and source/schema provenance, so
the same date and source can be reproduced later. Treat both files as a pair;
an incomplete or mismatched pair is rejected rather than used as a fallback.

To import an archive downloaded manually, use the explicit import workflow:

```python
from openNASR import CycleManager

cycle = CycleManager().import_archive(
    "/downloads/28DaySubscription_Effective_2024-06-13.zip"
)
```

Automatic downloads are a separate provider-backed workflow (`download()` or
`download_latest()`); they should be used only when a download provider is
configured. Importing a local archive never performs a network request.

## Quick start

The examples below are maintained against the public API and are covered by
the README example validation test. They require a locally installed FAA cycle
as described above; they never download data during tests.

Create a `NASR` object to load the most recent locally available cycle:

```python
from openNASR import NASR

nasr = NASR()
print(nasr.yearDecimal)
print(nasr["APT_BASE"].head())
```

Each CSV filename becomes a dictionary key. For example,
`APT_BASE.csv` is available as `nasr["APT_BASE"]`.

### Select a data cycle

Pass a cutoff date using ISO `YYYY-MM-DD` format. The loader selects the newest
local cycle earlier than the supplied date:

```python
nasr = NASR(useDate="2024-06-14")  # selects the 2024-06-13 cycle
```

Only cycles already present in `openNASR/data/zip/` can be selected. Supplying a
cutoff date emits a warning identifying the cycle that was selected.

## Airports

Airports can be requested by FAA location identifier or ICAO identifier:

```python
from openNASR import Airport, NASR

nasr = NASR()

bwi = Airport("BWI", nasr)
dca = Airport("KDCA", nasr)

print(bwi.faa_id)
print(bwi.icao_id)
print(bwi.lat, bwi.lon)
print(bwi.elevation)
```

Airport-related records are grouped by identifier:

```python
print(bwi.rwy.ids)
print(bwi.rwyend.ids)
print(bwi.ils.ids)

for runway_id in bwi.rwy.ids:
    runway = bwi.rwy[runway_id]
    print(runway_id, runway.length, runway.width)
```

Plot the airport layout using Matplotlib:

```python
bwi.plot(pltILSBnd=True)

from matplotlib import pyplot as plt

plt.show()
```

Runway geometry and projected coordinates use nautical miles.

## Fixes

```python
from openNASR import FIX

fix = FIX("AABEE", nasr)
print(fix.lat, fix.lon)
print(fix.lonlat)
print(fix.getRaw())
```

`getRaw()` returns the complete FAA record as a `SimpleNamespace`.

## Airport-linked airspace and military operations

The rich facade exposes airport-linked tables by the complete FAA site key;
short airport identifiers are intentionally not used as relationship keys:

```python
site_key = ("00000001A", "A")
class_airspace = nasr.class_airspaces.get(site_key)
military_operation = nasr.military_operations.get(site_key)

print(class_airspace.classes)
print(military_operation.call_sign)
```

When an airport site has matching data, `nasr.airport(...)` exposes it as
`airport.class_airspace` and `airport.military_operations`.

## Navigation network

Airways and holding patterns use their complete FAA composite identifiers;
their ordered child records retain FAA sequence values. Communication outlets
remain standalone because a communication location ID can be ambiguous.

```python
airway = nasr.airway(("Y", "D", "1"))
holding = nasr.holding_pattern(("ALPHA", "1", "FL", "US"))
frequency = nasr.frequency(("ALPHA", "A1", "A", "FL", "US", "121.5", "", "EMERGENCY"))

print([segment.point_sequence for segment in airway.segments])
print([remark.sequence for remark in holding.remarks])
print(frequency.record.serviced_facility_key)
```

`nasr.frequencies.find(serviced_facility=("A1", "A", "FL", "US"))`
requires the full serviced-facility context; it does not use a display name as
a relationship key.

## Navigation aids

```python
from openNASR import NAVAID

navaid = NAVAID("ABR", nasr)
print(navaid.lat, navaid.lon)
print(navaid.getRaw())
```

Some identifiers refer to more than one navigation aid. Optional selection
criteria include:

- `inCenter`: high- or low-altitude ARTCC identifier
- `inState`: state code
- `inCountry`: FAA country name
- `navType`: navigation-aid type

## Errors

All package-specific errors inherit from `OpenNASRError`. The public hierarchy
includes configuration, cycle, download, archive, table, schema, field
conversion, record-not-found, and ambiguous-record errors. Lookup ambiguity is
reported as `AmbiguousRecordError` with candidate records attached:

```python
from openNASR.exceptions import AmbiguousRecordError

try:
    nasr.navaid("DUP")
except AmbiguousRecordError as error:
    for candidate in error.candidates:
        print(candidate)
```

## ARTCC boundaries

`nasr.artccs.get(location_id)` / `nasr.artcc(location_id)` return a modern
`Artcc` object with the same `high`/`low` boundary geometry shown below. The
legacy `ARB` constructor remains available and unchanged:

Load ARTCC boundary records with `ARB`:

```python
from openNASR import ARB

airspace = ARB(nasr)
zob = airspace.getARTCC("ZOB")

print(zob.name)
print(zob.boundaryTypes)

high_boundary = zob.high
print(high_boundary.bbox)
print(high_boundary.lonlat[:5])

polygon = high_boundary.getShape
```

`getShape` returns a Shapely `Polygon`, which can be used for containment,
intersection, and other geometry operations.

Plot a geographic boundary with airports and intersecting airway segments:

```python
from openNASR import plot_airspace

figure, axes = plot_airspace(nasr, high_boundary)
```

The helper accepts a Shapely longitude/latitude polygon or a NASR boundary
object such as `high_boundary`. Install the optional plotting dependency with
`pip install -e '.[plot]'`.
Set `plot_high_airways`, `plot_low_airways`, `plot_airports`, `plot_fixes`, or
`plot_airnavs` to `False` to hide a layer; all are enabled by default.
Set `plot_legend=False` to hide the default layer legend.

Set `project_to_nm=True` to plot in east/north nautical miles using the local
gnomonic projection. By default its center is the airspace centroid; provide
`projection_center=(latitude, longitude)` to select a different center.

Use `plot_airport_procedures(nasr, "BWI")` to draw an airport's runways,
departure procedures, and standard terminal arrival routes.
Pass `project_to_nm=True` to use east/north nautical miles centered on that
airport, or provide `projection_center=(latitude, longitude)`.

All plotting helpers accept `project_to_nm=True` and an optional
`projection_center=(latitude, longitude)`. Airspace plots default to the
airspace centroid, airport procedure plots to the airport, and flight-plan
plots to the route center.

All plotting helpers include a legend by default. Pass `plot_legend=False` to
hide it.

## Special-use, sport, and military airspace

```python
maa = nasr.maa("AOH001")
parachute_jump_area = nasr.parachute_jump_area("PMD001")
route = nasr.military_training_route(("IR", "999"))

print(maa.record.type_name, maa.geometry)
print(parachute_jump_area.record.drop_zone_name, parachute_jump_area.airport)
print([point.identifier for point in route.points])
```

`Maa` covers the FAA's "Miscellaneous Activity Area" family — aerobatic
practice, glider, hang glider, space launch, ultralight, and unmanned-aircraft
areas — despite the acronym; it is unrelated to military airspace.
`ParachuteJumpArea.airport` is `None` for areas with no linked landing
facility. `MilitaryTrainingRoute` is keyed by `(ROUTE_TYPE_CODE, ROUTE_ID)`;
its points carry a distinct `identifier` from their display `sequence`,
matching the FAA's own documentation.

## Direct table access

`NASR` subclasses `dict`, so the original FAA tables can be queried directly
with pandas:

```python
maryland_airports = nasr["APT_BASE"].query("STATE_CODE == 'MD'")

vor_dmes = nasr["NAV_BASE"].query("NAV_TYPE == 'VOR/DME'")

bwi_runways = nasr["APT_RWY"].query("ARPT_ID == 'BWI'")
```

Available keys depend on the CSV files included in the selected FAA cycle:

```python
print(sorted(nasr.keys()))
```

## Coordinate conversion

The package includes helpers for a local gnomonic projection:

```python
from openNASR.cfcn import ll2xy, xy2ll

x, y, center, distance = ll2xy(
    lats=[38.85, 38.95],
    lons=[-77.10, -76.90],
    latc=38.90,
    lonc=-77.00,
)

lat, lon = xy2ll(x, y, latc=38.90, lonc=-77.00)
```

Coordinates returned by `ll2xy` and distances used by airport geometry are in
nautical miles.

## Data notes

- FAA data definitions and available tables may change between cycles.
- Missing values are represented according to pandas CSV parsing behavior.
- The library does not validate NASR data for operational use.
- Do not use this package as a sole source for navigation, flight planning, or
  safety-critical decisions.

## Current limitations

- NASR archives must be downloaded manually.
- `update=True` is reserved for future automatic download support.
- `preloadAll=True` is experimental.
- Procedure interfaces are not yet part of the public package API. The
  ``flight_plan_path`` helper resolves route fields only; it does not validate
  a flight plan for operational use.
- Only locally stored subscription cycles are available.

## Development

Run the example scripts from the repository root after installing the package:

```bash
python tests/main_test_NASR_airport.py
python tests/main_test_NASR_airspace.py
python tests/main_test_NASR_fix.py
python tests/main_test_NASR_navaid.py
python plotExamples/main_test_NASR_atlanta_procedures.py
python plotExamples/main_test_NASR_zob_airways.py
python plotExamples/main_test_NASR_airport_runways_ils.py --airport ATL
python plotExamples/main_test_NASR_runway_localizer_views.py --airport ATL --runway-end 08L
```

Contributions should avoid committing FAA archives, extracted cycle data,
generated figures, or Python cache files.

## License

openNASR is licensed under the GNU General Public License version 3. See
[`LICENSE`](LICENSE) for the full license text.

## Disclaimer

This project is not affiliated with or endorsed by the FAA. It is an
independent software library for working with publicly available FAA NASR data.
Always consult current official FAA publications and services for operational
aviation use.
