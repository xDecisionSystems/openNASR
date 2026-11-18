# Local mode

The same route resolution as the HTTP API, run on your machine from the cycle cache.
The JSON `opennasr route` prints is exactly the body `POST /v1/route/resolve` returns
(a test runs the same routes through both and requires identical output).

```sh
opennasr fetch                       # validated cycles from the bucket if OPENNASR_S3_BUCKET is set,
                                     # otherwise the FAA's current cycle
opennasr route "KABQ.DOOKK3.TXO..KTYR"
opennasr route "KABQ.DOOKK3.TXO..KTYR" --format table      # or --format geojson
opennasr route --icao-message "(FPL-UAL123-IS-B738/M-S-KABQ1530-N0450F350 ... -KTYR0210 ...)"
opennasr route "KMKE..ZJAYX.GRNCH5.KMCO" --strict           # exit 1 unless the route is complete
echo "KABQ ... KTYR" | opennasr route -                       # read the route from stdin
opennasr route "KABQ ... KTYR" --max-segment-nm 25           # add great-circle points
opennasr route "..." --cycle 2026-10-01                      # a specific cycle

opennasr serve                       # the HTTP API on 127.0.0.1:8000, prints a key for this session
opennasr serve --no-auth             # no key; loopback addresses only
opennasr serve --api-key KEY --host 0.0.0.0 --port 8080
```

- `route` uses the newest cached cycle already in effect (or `--cycle`). It builds the DuckDB file
  from a cached FAA zip the first time, or uses a fetched database as is.
- `fetch` with a bucket needs `pip install "openNASR-contract[s3]"` and the read-only settings
  (`OPENNASR_S3_*`, `OPENNASR_API_S3_*`; `--env-file` reads them from a file). Each database is
  verified against its manifest hash before it is installed. Without a bucket it downloads from the FAA.
- `serve` needs the API package (`pip install openNASR-api`). Rate limiting is off in local mode.
- Exit codes: 0 ok, 1 incomplete with `--strict`, 2 bad input, 3 source unavailable,
  4 data problem (for example no cycle cached), 5 unexpected error.
