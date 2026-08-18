# Using the library

openNASR works entirely on local FAA NASR subscription data. Downloading and
cache management are explicit operations; importing the package or creating a
`NASR` object never contacts the network.

## Install optional features

The base installation reads extracted FAA CSV tables:

```bash
python -m pip install openNASR
```

Install an extra only when its feature is needed:

```bash
python -m pip install "openNASR[plot]"
python -m pip install "openNASR[duckdb]"
```

## Download NASR data

The command-line interface is the simplest way to obtain the FAA's currently
advertised 28-day subscription:

```bash
opennasr check
opennasr download latest
opennasr list
```

`check` compares the newest cached cycle with the FAA's current-cycle page.
`download latest` downloads, validates, archives, and extracts that cycle.
The FAA provider exposes the currently advertised cycle, so an arbitrary
historical date may no longer be available remotely even though
`opennasr download YYYY-MM-DD` accepts an exact date.

For a historical ZIP obtained from the
[FAA 28-Day NASR Subscription page](https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/),
import the local archive explicitly:

```python
from openNASR import CycleManager

cycle = CycleManager().import_archive(
    "/downloads/28DaySubscription_Effective_2024-06-13.zip"
)
print(cycle.effective_date)
```

The filename must follow
`28DaySubscription_Effective_YYYY-MM-DD.zip`. Programmatic downloading also
requires an explicit provider:

```python
from openNASR.cycles import CycleManager, FaaCycleProvider

manager = CycleManager(provider=FaaCycleProvider())
cycle = manager.download_latest()
```

## Command-line interface

| Command | Purpose |
| --- | --- |
| `opennasr check` | Compare the newest cached and remote cycles. Use `--force` to refresh cached update metadata. |
| `opennasr download latest` | Download and extract the FAA's currently advertised cycle. |
| `opennasr download YYYY-MM-DD` | Request an exact cycle; it succeeds only when that date is already cached or is the cycle offered by the provider. |
| `opennasr list` | Show cached archives and extracted cycles. |
| `opennasr list --storage` | Also show whether each cycle has a ready DuckDB artifact. |
| `opennasr build-duckdb YYYY-MM-DD` | Build the DuckDB derivative for one cached cycle. `latest` selects the newest cached cycle. |
| `opennasr remove YYYY-MM-DD` | Remove that cycle's archive and extracted directory after confirmation. Use `--yes` for non-interactive operation. |

Run `opennasr COMMAND --help` for the complete arguments. Because the DuckDB
files live inside the extracted cycle directory, the CLI `remove` command also
removes that cycle's DuckDB derivative.

## Where data is saved

The cache root is selected in this order:

1. the `cache_dir=` argument passed to `CycleManager` or `NASR`;
2. the `OPENNASR_CACHE_DIR` environment variable; or
3. the platform-specific user cache directory selected by `platformdirs`.

Print the exact resolved location on the current computer with:

```python
from openNASR import CycleManager

print(CycleManager().cache_dir)
```

Typical defaults are `$XDG_CACHE_HOME/openNASR` (usually
`~/.cache/openNASR`) on Linux, `~/Library/Caches/openNASR` on macOS, and
`%LOCALAPPDATA%\openNASR\Cache` on Windows. These are examples; the command
above is authoritative for the current environment.

The cache is organized as follows:

```text
<cache>/
├── archives/
│   └── 28DaySubscription_Effective_YYYY-MM-DD.zip
├── cycles/
│   └── YYYY-MM-DD/
│       ├── ... extracted FAA files ...
│       ├── nasr.duckdb             # optional
│       └── nasr.duckdb.json        # DuckDB provenance
├── downloads/                      # temporary in-progress downloads
└── update-status.json              # cached update-check result
```

NASR archives and extracted tables are runtime data. They are not included in
the PyPI package and should not be committed to source control. Set a shared
or larger cache explicitly when the platform default does not have enough
space:

```python
manager = CycleManager(cache_dir="/data/nasr")
```

## Open a cycle

`NASR()` selects the newest locally cached cycle and reads CSV by default:

```python
from openNASR import NASR

nasr = NASR()
airports = nasr["APT_BASE"]
atl = nasr.airports.get("ATL")
```

For reproducible work, select the exact effective date:

```python
nasr = NASR(cycle="2024-06-13", storage="csv")
```

An absent exact cycle raises `CycleNotFoundError`; openNASR does not download
or substitute another date. FAA tables load lazily as pandas `DataFrame`
objects. Prefer domain repositories such as `nasr.airports`, `nasr.airways`,
and `nasr.stars` for keyed relationships, and raw tables for bulk analysis or
fields that do not yet have a domain convenience property.

## Choose CSV or DuckDB

CSV is the canonical source and the best default. DuckDB is an optional,
read-only derivative built from one exact extracted CSV cycle.

| Prefer CSV when | Prefer DuckDB when |
| --- | --- |
| You are exploring a few tables or making occasional lookups. | You repeatedly run selective queries over large tables. |
| You want the simplest installation and least additional disk use. | You want filters applied before rows are materialized as pandas data. |
| You need transparent access to the original extracted source tables. | You reuse many tables in an analysis and can afford a one-time build. |

Regular table and domain-object access still materializes pandas DataFrames
lazily in both modes, so DuckDB is not automatically faster for every
workflow. It also needs build time and extra disk space. Keep the extracted
CSV cycle as the source of truth; treat the database and its JSON provenance
sidecar as a replaceable pair.

Build and open a DuckDB artifact explicitly:

```bash
python -m pip install "openNASR[duckdb]"
opennasr build-duckdb 2024-06-13
opennasr list --storage
```

```python
nasr = NASR(cycle="2024-06-13", storage="duckdb")
```

DuckDB mode never builds a missing artifact, falls back to CSV, or selects a
nearby cycle. Rebuild the artifact after replacing its source cycle.

## Best practices

- Pin an exact effective date in analyses, tests, and historical flight-plan
  work; use `NASR()` without a date only when “newest cached” is intentional.
- Treat the DataFrames owned by a `NASR` instance as immutable. Request a copy
  before changing source data, and construct a new `NASR` after changing
  cycles or storage backends.
- Reuse `RouteResolver(nasr)` for batches of flight plans and
  `PlottingIndex(nasr)` for batches of plots. Both are snapshot-scoped;
  rebuild them after table replacement or mutation.
- Use repository `find(...)` methods for searches and `get(...)` for complete
  keys. Identifiers are normalized, but incomplete keys can be ambiguous.
- Keep cache data outside the repository and allow extra free space while
  building DuckDB because the completed artifact is replaced atomically.

## Coordinates and boundaries

`coordinates.ll2xy()` converts latitude/longitude to local east/north
nautical miles, and `coordinates.xy2ll()` performs the inverse conversion.
`Boundary` exposes `lonlat`, `latlon`, `bbox`, and its Shapely polygon through
`getShape`.

Plotting helpers support three coordinate systems:

- `projection="geographic"` returns longitude/latitude degrees;
- `projection="nautical_miles"` uses a local centered gnomonic projection;
- `projection="web_mercator"` returns EPSG:3857 x/y meters for Google Maps
  and other Web Mercator tile layers.

The older `project_to_nm=True` option remains an alias for the nautical-mile
projection. See {doc}`reference/plotting-coordinates` for generated plotting
signatures and full projection behavior.

## Errors

All public package failures derive from `OpenNASRError`. Catch a narrower
exception when the caller can recover from a particular condition:

| Exception | Meaning |
| --- | --- |
| `CycleNotFoundError` | The requested exact local cycle or storage artifact is absent. |
| `DownloadError` | Remote discovery or transfer failed. |
| `ArchiveError` | An archive or extracted cycle is invalid. |
| `TableNotFoundError` | The requested FAA table is unavailable. |
| `SchemaMismatchError` | Source columns do not match a supported schema. |
| `FieldConversionError` | A source value cannot be converted as documented. |
| `RecordNotFoundError` | A domain lookup or route token has no matching record. |
| `AmbiguousRecordError` | A key matches more than one candidate. |

Route processing also reports unsupported content and disconnected published
segments through typed `OpenNASRError` subclasses. See
{doc}`reference/exceptions` for the complete generated hierarchy.
