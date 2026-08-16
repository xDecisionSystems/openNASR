# Release status

The first supported openNASR release is designated **1.0.0**. This is the
appropriate compatibility boundary because the release establishes the stable
facade while retaining the documented legacy constructors and uppercase class
aliases throughout the `1.x` series.

The release is **not ready to publish**. The package version remains `0.0.1`
until the release blockers below are resolved and the complete release gate
passes.

## Release blockers

- `NASR` still discovers, extracts, and loads cycles beneath
  `openNASR/data/`, contrary to the external-cache requirement.
- An explicitly requested unavailable cycle can still select an earlier cycle
  instead of raising `CycleNotFoundError`.
- `NASR` eagerly loads every CSV rather than using the required lazy table
  repository.
- The documented `CycleManager` API is incomplete: `available_cycles()` and
  `latest()` are absent, and `CycleManager` is not exported from the package
  root used by the README examples.
- Several required Milestone 1 and complete-coverage regression checks remain
  unchecked in `PLAN.md`; their behavior must be implemented or verified
  before release readiness can be asserted.

After these blockers are cleared, run the full verification matrix in
`PLAN.md`, build both the wheel and source distribution, install the wheel in a
clean environment, and only then change package metadata and the changelog to
`1.0.0`.
