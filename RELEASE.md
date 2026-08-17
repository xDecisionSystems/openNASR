# Release guide

openNASR releases are built and published by GitHub Actions. The workflow uses
PyPI Trusted Publishing, so the repository does not need a long-lived PyPI API
token.

## One-time repository setup

1. Create a GitHub environment named `pypi`. Requiring a reviewer is
   recommended so a pushed tag cannot publish without explicit approval.
2. In PyPI, add a pending trusted publisher with these values:

   - PyPI project: `openNASR`
   - GitHub owner: `xDecisionSystems`
   - Repository: `openNASR`
   - Workflow: `publish-to-pypi.yml`
   - Environment: `pypi`

The pending publisher can create the first PyPI project when the package name
is still available. PyPI is the authority on package-name availability.

## Release checklist

1. Update `CHANGELOG.md` and set the release version in `pyproject.toml`.
2. Run the complete local gate from a clean checkout:

   ```bash
   python -m pytest
   ruff format --check openNASR tests benchmarks tools
   ruff check openNASR tests benchmarks tools
   mypy openNASR
   python -m build
   python -m twine check dist/*
   ```

3. Merge the release changes and confirm CI passes on `main`.
4. Create and push an annotated tag whose name exactly matches the package
   version:

   ```bash
   git tag -a v1.5.0 -m "openNASR 1.5.0"
   git push origin v1.5.0
   ```

5. Approve the `pypi` environment deployment, if protection is enabled.
6. Confirm the release on PyPI and install it in a clean environment.
7. Create GitHub release notes from the same tag.

The publish workflow rejects a tag that does not equal `v` plus the version in
`pyproject.toml`. It builds once, validates both distributions, and publishes
the exact artifacts produced by the build job.
