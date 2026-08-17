# Release status

The first supported openNASR release is designated **1.5.0**. This release
establishes the stable facade and includes the complete planned `1.x` rich
object coverage while retaining documented legacy constructors and uppercase
class aliases.

**All known engineering blockers are resolved and the full release gate
passes (2026-08-16).** Package metadata is now prepared for the completed
**1.5.0** feature set; publishing and tagging remain explicit release actions.

As of 2026-08-16, every task in PLAN.md (Milestones 0 through 12) is
complete, including the full `1.x` rich-object coverage plan originally
scoped as follow-on work beyond `1.0.0`. See "Remaining before publishing"
for what a version-number decision still needs to resolve.

## Release gate: last full run (2026-08-16)

All six commands passed end-to-end in one pass, in order, against a clean
checkout, re-verified after completing Milestone 12 (the last remaining
PLAN.md milestone):

```bash
python -m pytest              # 265 passed, 1 skipped
python -m ruff format --check .  # 90 files already formatted
python -m ruff check .        # All checks passed
python -m mypy openNASR       # Success: no issues found in 35 source files
python -m build                # wheel + sdist built successfully
python -m twine check dist/*  # both PASSED
```

Additionally verified beyond the six commands themselves:

- The built wheel contains no path under `openNASR/data/` (checked both the
  wheel's file listing and the actual installed files).
- Installing the wheel into a fresh virtual environment and importing
  `openNASR` from outside the source tree succeeds and resolves to the
  installed package, not the source checkout.

Two real, non-cosmetic fixes came out of this run, not just formatting:
`ruff format` reformatted code written by hand across three sessions of
Milestone 4B/5B work (`nasr.py`, `repository.py`, `fix.py`,
`test_nasr_facade.py`), and two long f-string lines in
`tools/generate_schema_manifests.py` needed manual wrapping since the
formatter cannot safely split f-strings on its own. No test assertions or
production logic changed; `pytest` was re-run after each fix and stayed
green throughout.

## Repository ownership (2026-08-16)

Ownership has moved and been confirmed: pushing to the old
`https://github.com/ADCLab/openNASR` remote returned GitHub's "This
repository moved" redirect notice, pointing at
`https://github.com/xDecisionSystems/openNASR`. The local `origin` remote
and the live references in `README.md` and `pyproject.toml` now point at
the new location (PLAN.md Task 7.14).

## Remaining before publishing

Nothing engineering-blocking remains. Create the `v1.5.0` tag and publish the
prepared package when release authority is granted.

As of 2026-08-16, **every task in PLAN.md is checked off** — Milestones
8-12 (the complete `1.x` rich-object coverage plan: `atc`/`weather`/
`airway`/`routes`/`communications`/`fss`/`holding`/`locations`/`military`/
`CLS_ARSP`/`MAA_*`/`PJA_*`/`MTR_*`) are now done, not merely scheduled.
These were explicitly out of scope for `1.0.0` itself (see "Complete FAA
CSV coverage plan > Relationship to the initial 1.0.0 release" in
PLAN.md), so their completion does not change what's required to cut
`1.0.0`, but it does mean a `1.5.0` release (or a combined release
covering everything through `1.5.0`) could also be cut with no further
engineering work, once a versioning decision is made for that too.

## Historical: engineering blockers resolved before this file was last written

- `NASR` now discovers, extracts, and loads cycles through `CycleManager`,
  resolving the cache directory via the documented `cache_dir` ->
  `OPENNASR_CACHE_DIR` -> platform-default precedence. It no longer reads
  `Path(__file__).parent` or writes into the installed package directory.
  (PLAN.md Milestone 4B, tasks 4B.8-4B.9, 4B.12.)
- An explicitly requested cycle that is not present in the cache now raises
  `CycleNotFoundError` naming the requested date; it never silently
  substitutes an earlier cycle. (Milestone 4B, tasks 4B.10-4B.11.)
- `NASR` now loads tables lazily through `TableRepository`, only when a
  table is actually requested (directly or through a repository), instead
  of eagerly reading every CSV in the cycle at construction time. Per-table
  schema validation is similarly deferred to first access, so drift in one
  table never blocks constructing `NASR` or using an unrelated table.
  (Milestone 4B, tasks 4B.13-4B.16.) Fixing this also surfaced and fixed a
  latent bug where `FixRepository`/`NavaidRepository` eagerly loaded
  `FIX_BASE`/`NAV_BASE` regardless of whether the caller needed them.
- The documented `CycleManager` API is now complete: `available_cycles()`
  and `latest()` are implemented and tested, `remove()` accepts
  `archive=`/`extracted=` keywords and reports what it removed, and
  `CycleManager` is exported from the package root used by the README
  examples.
- `opennasr check`/`opennasr download`, invoked with no injected manager,
  default to a working `FaaCycleProvider` that discovers the current cycle
  from the real FAA subscription page, and the CLI maps failures to typed,
  documented exit codes instead of crashing with an unhandled traceback.
- `nasr.artccs`/`nasr.artcc(identifier)` now exist as a modern
  repository-based facade, matching the contract every other required-for-
  `1.0.0` family already had. It wraps the existing, already-correct
  boundary geometry in `openNASR/arb.py`'s `Boundary` class (verified with
  exact Shapely `.equals()` comparisons, not just bbox) rather than
  reimplementing it. `TableRegistry().table("ARB_BASE").record_type` now
  returns `ArtccRecord`. The legacy `ARB`/`nasr.loadARTCC()`/`nasr.artcc`
  (singular attribute) path is unchanged and still works. (Milestone 5B.)

See "Release gate: last full run" above for the current, complete gate
status.
