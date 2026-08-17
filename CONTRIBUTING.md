# Contributing

## Development setup

Use Python 3.10 or newer and install the editable package with development and
optional plotting dependencies:

```bash
python -m pip install -e ".[dev,plot,duckdb,release]"
```

## Verification

Run the focused tests while iterating, then the full suite and static checks:

```bash
python -m pytest
ruff format --check openNASR tests benchmarks tools
ruff check openNASR tests benchmarks tools
mypy openNASR
python -m build
python -m twine check dist/*
```

The repository’s deterministic FAA fixtures live under `tests/fixtures/`.
Tests should use those fixtures or temporary directories rather than a user’s
installed data cache or the network.

## Changes

Add or update tests for behavior changes, keep raw FAA values lossless, update
the relevant plan checkbox and documentation, and use a descriptive commit
message. Do not commit downloaded NASR archives or extracted cycle data.

Open a pull request against `main`. CI must pass on every supported Python
version before merge. Report security issues privately as described in
[SECURITY.md](SECURITY.md), rather than opening a public issue.
