# DuckDB benchmark report — `<cycle or fixture set>`

Use this template for a manually run report. Keep the raw JSON output outside
the repository; this document is a form for summarizing that output and never
contains FAA archives, extracted cycles, or database files.

## Run identity

| Field | Value |
| --- | --- |
| UTC timestamp | `<...>` |
| Exact effective cycle | `<YYYY-MM-DD>` |
| Dataset / fixture | `<...>` |
| Git commit / dirty state | `<...>` |
| Command and arguments | `<...>` |
| Cache/output paths | `<paths outside repository>` |

## Machine and software

Record OS/kernel, architecture, CPU model and logical CPU count, total RAM,
filesystem/mount type, rotational status, Python, openNASR, pandas, and DuckDB
versions. Do not describe a result as filesystem-cold: cold repetitions mean a
fresh Python process with a read-only database connection and empty application
caches.

## Dataset and provenance

| Measure | CSV | DuckDB |
| --- | ---: | ---: |
| Table/file count | `<...>` | `<...>` |
| Row count | `<...>` | `<...>` |
| Total bytes | `<...>` | `<...>` |
| Archive bytes / SHA-256 | `<...>` | `<...>` |
| Schema ID/fingerprint | `<...>` | `<...>` |
| Sidecar bytes | `n/a` | `<...>` |
| Storage format version | `n/a` | `<...>` |

## Workload results

Report median, p95, minimum, median absolute deviation, and raw samples from
the JSON output. Report RSS/peak RSS and materialized row/column counts where
available. CSV and DuckDB must use the same preselected keys and workload
order.

| Workload | CSV median/p95 | DuckDB median/p95 | RSS | Notes |
| --- | --- | --- | --- | --- |
| Build and validation | `<...>` | `<...>` | `<...>` | `<...>` |
| Fresh construction | `<...>` | `<...>` | `<...>` | `<...>` |
| First table access | `<...>` | `<...>` | `<...>` | `<...>` |
| Repeated table access | `<...>` | `<...>` | `<...>` | `<...>` |
| `copy=True` access | `<...>` | `<...>` | `<...>` | `<...>` |
| Airport identity hit/miss | `<...>` | `<...>` | `<...>` | `<...>` |
| Fix identity hit/miss | `<...>` | `<...>` | `<...>` | `<...>` |
| Navaid identity hit/miss | `<...>` | `<...>` | `<...>` | `<...>` |
| Airway relationship hit/miss | `<...>` | `<...>` | `<...>` | `<...>` |

## Correctness and selected keys

List the deterministic hit and not-found keys, index definitions, and any
index build time/size delta. Confirm that parity was checked before timings:
public values, ordering, DataFrame dtypes/cells, and exception classes. Record
all skipped or failed workloads with a reason.

## Decision

- [ ] CSV/DuckDB parity passed for this dataset.
- [ ] The real exact cycle was available; no cycle fallback was used.
- [ ] Build, construction, first-access, warm-access, and lookup results are
      reported separately.
- [ ] Any retained physical index has an A/B result showing a material win.
- [ ] The result is sufficient / insufficient for the Phase 13.4 gate.

Conclusion: `<state whether DuckDB is recommended for this workload and why>`
