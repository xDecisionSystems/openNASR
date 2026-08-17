# Queries, schemas, and storage

The query API is deliberately bounded and read-only. CSV and DuckDB backends
share source ordering, exact-cycle provenance, and typed error behavior.
DuckDB is an optional dependency and its artifacts are immutable derivatives
of extracted FAA CSV cycles.

## Bounded table queries

```{eval-rst}
.. automodule:: openNASR.query
```

## Storage contract and implementations

```{eval-rst}
.. automodule:: openNASR.storage
```

```{eval-rst}
.. automodule:: openNASR.duckdb_tables
```

```{eval-rst}
.. automodule:: openNASR.duckdb_builder
```

```{eval-rst}
.. automodule:: openNASR.duckdb_metadata
```

## Schema and table registry

```{eval-rst}
.. automodule:: openNASR.schemas
```

```{eval-rst}
.. automodule:: openNASR.registry
```
