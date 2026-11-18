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
   git tag -a v2.0.0 -m "openNASR 2.0.0"
   git push origin v2.0.0
   ```

   The tag starts only the **signed deployment release** (`release.yml`): it
   tests the tag, builds the four wheels and the updater, signs the manifest and
   publishes a GitHub release.
5. Confirm the signed GitHub deployment release exists for the same tag.
6. **PyPI is a separate, deliberate step.** In GitHub, open Actions, choose
   "Publish to PyPI", pick the release tag as the ref and run it, then approve the
   `pypi` environment deployment. The workflow rejects a ref that does not equal
   `v` plus the version in `pyproject.toml`, builds once, validates both
   distributions, and publishes the exact artifacts it built.
7. Confirm the release on PyPI and install it in a clean environment.

## Signed deployment releases

The tag also starts `release.yml`. It tests the tag, builds the four project
wheels, and publishes them with `opennasr-update`, `manifest.json`, and the
Sigstore bundle. The manifest records the tag, commit, and asset hashes.
Protect release tags with a GitHub tag ruleset. The PyPI workflow never runs from a tag push; it is started by hand (step 6).

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
on a different port. Before switching the archiver, the updater runs its
read-only `status` command as the service account with the systemd environment
file. If bucket access fails, the current release stays active. The regular
archiver timer picks up the update on its next run.

To restore the previous executable, run `opennasr-update --role api --rollback`
or `opennasr-update --role archiver --rollback` on the applicable guest.
The updater also restores the previous API executable if the readiness check
fails. Archiver rollback remains available during a bucket outage.
Rollback switches code only. Service configuration, cached data, and
archiver state stay in their existing locations. The original installer venv
remains on disk. After a successful switch, the updater removes superseded
release venvs for that role while keeping the active and rollback venvs. It
defers cleanup when an archiver run is in progress.
