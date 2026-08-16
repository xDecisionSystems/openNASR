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
