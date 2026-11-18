# openNASR

Resolve FAA flight-plan routes to latitude/longitude paths from FAA NASR data, plus the
service that keeps the data current. Same input and same cycle always give the same output.

| Directory | What it is |
|---|---|
| [`core/`](core/) | The `openNASR` Python library and the `opennasr` command (route, serve, fetch, cycle tools). Its README is [`core/README.md`](core/README.md). |
| [`contract/`](contract/) | The bucket key layout, manifest and bucket clients shared by the archiver and the API. |
| [`archiver/`](archiver/) | Downloads each FAA cycle, builds and validates the DuckDB file, publishes to S3. |
| [`api/`](api/) | The read-only HTTP API (`docs/openapi.json`). |
| [`deploy/`](deploy/) | Proxmox installer, signed-release updater and the read-only production check. |
| `tests/`, `tools/`, `docs/`, `benchmarks/` | Shared tests, tools, documentation and benchmarks. |

Start with [`HANDOVER.md`](HANDOVER.md) (current state, how to build and test, pitfalls) and
[`REPLAN.md`](REPLAN.md) (plan and decisions). Developer setup is in [`CONTRIBUTING.md`](CONTRIBUTING.md);
releases are in [`RELEASE.md`](RELEASE.md).

```sh
python -m pip install -e "./core[dev,plot]"
python -m pytest
```

Licence: GPL-3.0-only (see [`LICENSE`](LICENSE)).
