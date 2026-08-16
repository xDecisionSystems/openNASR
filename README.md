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
- Look up fixes and navigation aids.
- Build ARTCC boundary polygons with Shapely.
- Convert latitude/longitude coordinates to local nautical-mile coordinates.
- Plot airport runways and ILS information with Matplotlib.

## Requirements

- Python 3.10 or newer
- pandas
- NumPy
- Shapely
- Matplotlib (optional; required only for plotting)

## Installation

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/ADCLab/openNASR.git
cd openNASR
python -m pip install -e .
```

Editable installation is recommended while the package is in development.

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

## ARTCC boundaries

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
- Airway, departure, and flight-plan interfaces are not yet part of the public
  package API.
- Only locally stored subscription cycles are available.

## Development

Run the example scripts from the repository root after installing the package:

```bash
python tests/main_test_NASR_airport.py
python tests/main_test_NASR_airspace.py
python tests/main_test_NASR_fix.py
python tests/main_test_NASR_navaid.py
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
