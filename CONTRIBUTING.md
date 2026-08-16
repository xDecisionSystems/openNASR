# Contributing

## Development setup

Use Python 3.10 or newer and install the editable package with development and
optional plotting dependencies:

```bash
python -m pip install -e ".[dev,plot]"
```

## Verification

Run the focused tests while iterating, then the full suite and static checks:

```bash
python -m pytest
ruff format --check openNASR tests
ruff check openNASR tests
mypy openNASR
```

The repository’s deterministic FAA fixtures live under `tests/fixtures/`.
Tests should use those fixtures or temporary directories rather than a user’s
installed data cache or the network.

## Changes

Add or update tests for behavior changes, keep raw FAA values lossless, update
the relevant plan checkbox and documentation, and use a descriptive commit
message. Do not commit downloaded NASR archives or extracted cycle data.
