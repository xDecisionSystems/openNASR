# Release status

The first supported openNASR release is designated **1.0.0**. This is the
appropriate compatibility boundary because the release establishes the stable
facade while retaining the documented legacy constructors and uppercase class
aliases throughout the `1.x` series.

**All known engineering blockers are resolved and the full release gate
passes (2026-08-16).** The package version remains `0.0.1` pending an
explicit decision to cut the `1.0.0` release (a packaging/versioning action,
not an engineering one — see "Remaining before publishing" below).

## Release gate: last full run (2026-08-16)

All six commands passed end-to-end in one pass, in order, against a clean
checkout:

```bash
python -m pytest              # 238 passed, 1 skipped
python -m ruff format --check .  # 89 files already formatted
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

## Remaining before publishing

Nothing engineering-blocking remains. What's left is a release *decision*,
not a defect:

- Decide and set the actual `1.0.0` version number in `pyproject.toml` and
  `CHANGELOG.md` (currently `0.0.1`), and cut the release.
- Task 7.14 (updating the Git remote from the moved ADCLab repository) is
  explicitly non-blocking and depends on an external ownership confirmation
  — track separately, do not let it hold up `1.0.0`.
- PLAN.md's Milestones 8-12 (rich-object coverage for `atc`/`weather`/
  `airway`/`routes`/`communications`/`fss`/`holding`/`locations`/`military`/
  `CLS_ARSP`/`MAA_*`/`PJA_*`/`MTR_*`) are explicitly scheduled as `1.x`
  follow-on releases (`1.1.0` through `1.5.0`), not `1.0.0` requirements —
  see "Complete FAA CSV coverage plan > Relationship to the initial 1.0.0
  release" in PLAN.md.

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
