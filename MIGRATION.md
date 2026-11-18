# Migration guide

## Namespace

The package remains importable as `openNASR`. Existing uppercase compatibility
classes continue to work, while new code should prefer the facade methods:

| Legacy | Preferred |
| --- | --- |
| `FIX("AABEE", nasr)` | `nasr.fix("AABEE")` |
| `NAVAID("ABR", nasr)` | `nasr.navaid("ABR")` |
| `ARB(nasr).getARTCC("ZOB")` | `nasr.artccs.get("ZOB")` when available |
| `Airport("BWI", nasr)` | `nasr.airport("BWI")` |

Legacy constructors are retained for compatibility with existing applications.
The facade repositories provide normalized identifiers, typed properties, and
deterministic not-found/ambiguous lookup errors.

## Raw and typed values

Use a record’s `raw` mapping or `as_dict()` when exact FAA source values are
needed. Typed properties convert validated values without changing those raw
strings; empty fields become `None` in the typed layer.

## Exceptions

Catch the specific `openNASR.exceptions` class relevant to the operation,
especially `RecordNotFoundError` and `AmbiguousRecordError`, rather than
matching legacy printed output.

## DuckDB storage (2.0)

openNASR 2.0 serves every cycle from a DuckDB artifact; CSV storage was removed.

- `NASR(..., storage="csv")` now raises `ConfigurationError`. Drop the argument
  (or pass `storage="duckdb"`, which is the only value).
- The first `NASR(...)` for a cycle builds the artifact from its archive or CSVs.
  Build ahead of time with `opennasr build-duckdb 2024-06-13`.
- `duckdb` is now a required dependency (the `openNASR[duckdb]` extra is gone).
  It is capped below 2.0 because the 2.0.0 wheel needs AVX2 CPUs.
- `openNASR.tables.TableRepository` and the CSV query fallback were removed.
- Raw tables are always source text (as with real FAA data). Fixtures that
  relied on pandas inferring numbers now see strings such as `"121.500"`.
- Existing artifacts built by 1.x use sidecar format 1 and are rebuilt
  automatically when sources are present.
