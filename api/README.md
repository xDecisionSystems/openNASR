# openNASR API

Read-only HTTP API over validated FAA NASR cycles. The headline endpoint resolves a
flight-plan route to an ordered list of latitude/longitude points, each with its source
(`kind`, `via`, `segment`), plus GeoJSON and structured diagnostics. The full contract is
[`docs/openapi.json`](../docs/openapi.json); the live service serves it at `/docs`.

```
POST /v1/route/resolve   {"route": "KABQ.DOOKK3.TXO..KTYR"}        # or {"icao_message": "(FPL-...)"}
GET  /v1/route/resolve?route=...&max_segment_nm=20                    # opt-in great-circle densify
GET  /v1/airports/{id}  /v1/fixes/{id}  /v1/navaids/{id}  /v1/airways/{id}
GET  /v1/airspace/at?lat=&lon=       # ARTCC / FIR / CTA / UTA containing a point
GET  /v1/cycles   /health   /ready
```

Every request except `/health` and `/ready` needs `X-API-Key: <key>` (or `Authorization: Bearer`).
Limits are per key (`OPENNASR_API_RATE_PER_MINUTE`, default 120); a limited request gets 429 with
`Retry-After`. Each response carries `X-Request-ID` (send your own to correlate); the access log is one
JSON line per request with a short key label, never the key or the route text.

A route that cannot be fully resolved is still a 200: read `complete` and `diagnostics`. Branches that
depend on runway or airport configuration return only the shared portion and a `procedure_branches`
warning. Class B/C/D/E airspace is not in the FAA CSV data as polygons, so `/v1/airspace/at` does not
search it (the response says so).

## Install

User `opennasr`; a venv at `/opt/openNASR/venv` with `pip install openNASR ./contract[s3] ./api`;
`api/deploy/openNASR-api.service` to `/etc/systemd/system/`; settings in `/etc/openNASR/api.env`
(see `deploy/api.env.example`); then `systemctl enable --now openNASR-api`. The service fetches
verified cycles from the bucket at start and hourly, and keeps serving what it has if the bucket is
down. Put a TLS reverse proxy (NPMplus) in front; the service itself speaks plain HTTP. The installer
must choose a working DuckDB version for the CPU (REPLAN.md, "DuckDB version selection").

On proxopotamus use `deploy/proxmox/install.sh --role api`. Set `OPENNASR_API_KEYS` for key auth, or `OPENNASR_API_AUTH=none` to run without keys on a private network (it logs a warning).
