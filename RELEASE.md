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

1. Update `CHANGELOG.md` and set the release version in `core/pyproject.toml`.
2. Run the complete local gate from a clean checkout:

   ```bash
   python -m pytest
   ruff format --check core/openNASR contract archiver api tests benchmarks tools
   ruff check core/openNASR contract archiver api tests benchmarks tools
   MYPYPATH=contract:archiver:api mypy core/openNASR contract/openNASR_contract archiver/openNASR_archiver api/openNASR_api
   python -m build --outdir dist core
   python -m twine check dist/*
   ```

3. Merge the release changes and confirm CI passes on `main`.
4. Create and push an annotated tag whose name exactly matches the package
   version:

   ```bash
   git tag -a v2.0.1 -m "openNASR 2.0.1"
   git push origin v2.0.1
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
wheels, and publishes them with `opennasr-update`, dependency locks for the API
and archiver, `manifest.json`, and the Sigstore bundle. The manifest records
the tag, commit, and asset hashes.
Protect release tags with a GitHub tag ruleset. The PyPI workflow never runs from a tag push; it is started by hand (step 6).

### Update an existing systemd guest

Run these commands as root inside the guest. Install a trusted Cosign binary
first. Refresh the updater itself before moving from `v2.0.0` to a release
with dependency locks. The script shipped in `v2.0.0` expects the original
manifest format.

```sh
set -eu
tag=v2.0.1
repo=https://github.com/xDecisionSystems/openNASR
cd "$(mktemp -d)"
for asset in manifest.json manifest.json.sigstore.json opennasr-update; do
  curl --fail --silent --show-error --location --output "$asset" \
    "$repo/releases/download/$tag/$asset"
done
/usr/local/bin/cosign verify-blob --bundle manifest.json.sigstore.json \
  --certificate-identity "$repo/.github/workflows/release.yml@refs/tags/$tag" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com manifest.json
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

expected = json.loads(Path("manifest.json").read_bytes())["assets"]["opennasr-update"]
if hashlib.sha256(Path("opennasr-update").read_bytes()).hexdigest() != expected:
    raise SystemExit("Updater hash mismatch")
PY
install -m 0755 opennasr-update /usr/local/sbin/opennasr-update
```

Then run the command for the applicable guest.

```sh
export PATH="/usr/local/bin:/usr/local/sbin:$PATH"
/usr/local/sbin/opennasr-update --role api --version v2.0.1
/usr/local/sbin/opennasr-update --role archiver --version v2.0.1
```

The updater pins the signature to the release workflow in this repository at
the exact tag and verifies the selected project wheels before installing them.
For release manifests with dependency locks, pip installs the role's exact
third-party wheel versions with hash checking. DuckDB uses the version
recorded by the guest installer and is installed separately. The original
`v2.0.0` release predates locks and still resolves its other dependencies at
install time. The update probes DuckDB in a
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
