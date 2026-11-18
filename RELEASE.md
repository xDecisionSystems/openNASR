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
7. Confirm the signed GitHub deployment release was published for the same tag.

The publish workflow rejects a tag that does not equal `v` plus the version in
`pyproject.toml`. It builds once, validates both distributions, and publishes
the exact artifacts produced by the build job.

## Signed deployment releases

The tag also starts `release.yml`. It tests the tag, builds the four project
wheels, and publishes them with `opennasr-update`, `manifest.json`, and the
Sigstore bundle. The manifest records the tag, commit, and asset hashes.
Protect release tags with a GitHub tag ruleset. The PyPI and deployment
release workflows have separate jobs and run independently.

### Update an existing systemd guest

Run these commands as root inside the guest. Install a trusted Cosign binary
first. Bootstrap the updater from the trusted repository checkout at the
desired release tag, or verify the release manifest and the updater hash
before installing the downloaded script.

```sh
install -m 0755 deploy/opennasr-update /usr/local/sbin/opennasr-update
opennasr-update --role api --version v2.0.0
# On the archiver guest
opennasr-update --role archiver --version v2.0.0
```

The updater pins the signature to the release workflow in this repository at
the exact tag and verifies the selected project wheels before installing them.
Pip resolves third-party dependencies separately, and DuckDB stays pinned to
the version recorded by the guest installer. The update probes DuckDB in a
new virtual environment before changing the service's systemd executable.
The API restarts and must pass `/ready`. Use `--ready-url` if the guest listens
on a different port. The archiver timer picks up the update on its next run.

To restore the previous executable, run `opennasr-update --role api --rollback`
or `opennasr-update --role archiver --rollback` on the applicable guest.
The updater also restores the previous API executable if the readiness check
fails. Rollback switches code only. Service configuration, cached data, and
archiver state stay in their existing locations. The original installer venv
and staged release venvs remain on disk.
