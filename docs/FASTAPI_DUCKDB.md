# FastAPI integration with DuckDB

This note describes a future HTTP service around openNASR. It is an integration
contract, not a shipped FastAPI application: openNASR does not depend on
FastAPI, start an HTTP server, or download/build data in response to a request.

## Process and connection lifecycle

Build each cycle with `CycleManager.build_duckdb()` before deployment. At
FastAPI lifespan startup, the service should discover only completed
`nasr.duckdb`/`nasr.duckdb.json` pairs, validate their provenance, and create a
bounded, per-cycle pool of DuckDB connections opened with `read_only=True`.
Connections belong to one worker process and are closed during lifespan
shutdown. A checked-out connection must be used by only one request at a time;
do not share an active connection or cursor between request threads.

Pool creation may be lazy after startup validation so a service with many
historical cycles does not open every database immediately. Set a small fixed
per-process pool bound and an acquisition timeout. Pool exhaustion should
produce a temporary service error, not an unbounded connection or task queue.
The application may cache immutable cycle metadata, but request result pages
remain bounded by the query contract.

Publishing is an offline administrative operation. A builder publishes a
validated database and sidecar atomically, then the service refreshes its cycle
catalog between requests or during an explicit reload. The HTTP process never
opens a writable connection, steals a build lock, repairs an artifact, or falls
back to CSV when a DuckDB artifact is absent or invalid.

## Cycle selection

A request supplies exactly one of these selectors:

- `cycle=YYYY-MM-DD` selects that exact FAA effective date. An unavailable
  cycle is a not-found error; no neighboring cycle is substituted.
- `as_of=YYYY-MM-DD` selects the greatest locally published effective date that
  is less than or equal to the supplied date. It never selects a future cycle.
  If no qualifying cycle exists, the result is a not-found error.

Supplying both selectors or neither is a validation error. For the query
operation defined in `DUCKDB_PLAN.md`, a service can expose
`POST /v1/query?cycle=...` and `POST /v1/query?as_of=...`. The exact-cycle
convenience route `POST /v1/cycles/{cycle}/query` has identical behavior to the
first form and must reject an additional `cycle` or `as_of` selector. Use the
exact `cycle` form when reproducibility matters; `as_of` is a deliberate
effective-on-date lookup rather than an exact-date alias.

Normalize selectors as ISO calendar dates before constructing cache paths.
Never accept a client-provided filesystem path or database filename. Resolve
the selected date against the lifespan-managed, validated cycle catalog.

## Query and response contract

The transport maps only to `NASR.query_table(...)`: allowlisted table/field
identifiers, `EQ`/`IN` filters joined by `AND`, and bound values. It does not
expose raw SQL, expressions, joins, caller-defined ordering, mutable statements,
or a general DuckDB connection.

Every successful page should include the `QueryPage` fields and a provenance
object such as:

```json
{
  "requested": {"as_of": "2026-08-17"},
  "resolved_cycle": "2026-08-06",
  "schema_fingerprint": "...",
  "archive_sha256": "...",
  "database_sha256": "...",
  "storage_format_version": 1,
  "backend": "duckdb"
}
```

For an exact request, `requested` contains `cycle` instead. Values come from
the validated sidecar, not client input. Deployments may add a service build
identifier and request ID, but must not reveal SQL, bound values, local paths,
cursor internals, or connection errors.

Use the opaque cursor pagination defined by `QueryPage`; do not translate it
to offset pagination. The first release permits page sizes from 1 through
1,000 (default 100) and stops before an 8 MiB JSON-equivalent page. A service
may configure smaller page, request-body, and response-body limits, but never
larger library limits. Cursors remain bound to the resolved effective date,
schema fingerprint, query, projection, and page size. A changed selector or
request invalidates the cursor.

## HTTP behavior and deployment limits

Suggested mappings are 422 for selector/query/cursor validation, 404 for an
unavailable cycle/table, 413 for a row that cannot fit the payload limit, 503
for pool-acquisition timeout or an unavailable artifact during catalog reload,
and 500 for a redacted unexpected storage failure. Add authentication,
authorization, TLS, rate limiting, request timeouts, and audit logging at the
service or gateway according to the deployment's exposure; openNASR does not
provide those controls.

DuckDB is best treated here as an immutable, read-heavy, single-node artifact.
Each FastAPI worker has its own connection pools and pandas/object caches, so
worker count multiplies connection count and memory use. Bound both, measure
with the production cycle size, keep the databases on reliable local storage,
and budget disk space for source archives, extracted CSVs, the current
artifacts, and an atomic replacement during publication. Read-only replicas
may be copied to multiple hosts, but each host must validate the database and
sidecar pair and operators must coordinate catalog rollout. Do not put request
traffic and ingestion writes through the same database files.

The first release does not load DuckDB extensions at runtime. Existing Shapely
geometry remains suitable when spatial work is modest and performed after a
bounded NASR query. CPU-heavy plotting or geometry construction should run in
a separately bounded worker/job path rather than tying up request handlers.

## When to use DuckDB or PostGIS

Use per-cycle DuckDB when the workload is primarily exact-date FAA table and
repository lookups, artifacts fit on each service host, publication is
batch-oriented, and concurrency can be satisfied by bounded read-only pools.
It has a simple reproducible artifact boundary and keeps the library's local
workflow intact.

Evaluate PostGIS only when spatial multi-user requirements dominate: many
concurrent users need indexed intersection, containment, distance, or
bounding-box queries; application workers must share one transactional source;
or operational needs require centralized access control, replication, online
publication, and database observability. PostGIS adds service infrastructure,
schema migration, ingestion, and availability responsibilities and should not
replace DuckDB merely to serve non-spatial NASR lookups. A future service may
materialize selected cycle data into PostGIS while retaining the FAA archive,
CSV extraction, and provenance metadata as the source-of-record chain.

