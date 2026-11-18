# Contributing

## Development setup

Use Python 3.10 or newer and install the editable package with development and
optional plotting dependencies:

```bash
python -m pip install -e "./core[dev,plot,release]"
```

## Verification

Run the focused tests while iterating, then the full suite and static checks:

```bash
python -m pytest
ruff format --check core/openNASR contract archiver api tests benchmarks tools
ruff check core/openNASR contract archiver api tests benchmarks tools
MYPYPATH=contract:archiver:api mypy core/openNASR contract/openNASR_contract archiver/openNASR_archiver api/openNASR_api
python -m build --outdir dist core
python -m twine check dist/*
```

The repository’s deterministic FAA fixtures live under `tests/fixtures/`.
Tests should use those fixtures or temporary directories rather than a user’s
installed data cache or the network.

## Changes

Add or update tests for behavior changes, keep raw FAA values lossless, update
the relevant plan checkbox and documentation, and use a descriptive commit
message. Do not commit downloaded NASR archives or extracted cycle data.

Commit directly to `main`; CI must pass on every supported Python version. Report security issues privately as described in
[SECURITY.md](SECURITY.md), rather than opening a public issue.
