# Synthetic NASR fixtures

These fixtures contain only headers from the checked-in FAA schema manifests
and purpose-built synthetic values. They contain no FAA operational records.

- `schema_only/` has every supported CSV filename with its exact header for
  each schema generation.
- `core/pre_2026_09/` has the small relationship set used by Milestone 1
  regressions: two airports, reciprocal runway ends, ILS components, one fix,
  unique and duplicate navaids, and high/low ARTCC boundaries.
- `relationships/airport_linked.json` contains fabricated rows for both schema
  generations that verify `CLS_ARSP` and `MIL_OPS` joins by the complete
  airport site key, including deliberately duplicated short airport IDs.

Run `python tools/build_synthetic_fixtures.py` after intentionally changing a
manifest or synthetic fixture definition.
