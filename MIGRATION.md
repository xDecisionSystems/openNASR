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

## Optional DuckDB storage

CSV remains the default storage mode. Install the optional dependency and
explicitly build an artifact for each reproducible effective date:

```bash
python -m pip install -e ".[duckdb]"
opennasr build-duckdb 2024-06-13
```

Then pass both the exact cycle and backend when constructing `NASR`:

```python
nasr = NASR(cycle="2024-06-13", storage="duckdb")
```

DuckDB is a read-only derivative; it does not replace or mutate source CSVs.
Missing, incomplete, or incompatible artifacts raise a typed error. Rebuild
the selected cycle explicitly after source data changes, and use
`CycleManager.remove(date, archive=False, extracted=False, duckdb=True)` to
remove only its database and sidecar.
