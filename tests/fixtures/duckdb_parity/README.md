# DuckDB CSV parity fixtures

These deliberately tiny, text-only cycles are shared by CSV and DuckDB parity
tests. They contain no FAA records. Each generation has the same two tables,
`APT_RWY` and `FIX_BASE`, while preserving the real schema distinction in
`APT_RWY` (`PCN` before 2026.09 versus `PAVEMENT_CLASSIFICATION` and
`PCN_PCR_NUMBER` in 2026.09).

The values cover lossless CSV concerns: zero-padded text, empty cells, quoted
commas and newlines, Unicode, and duplicate identifiers.
