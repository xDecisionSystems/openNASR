"""Exercise signed asset selection and service rollback without a live guest."""

import hashlib
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def updater():
    script = Path(__file__).parents[1] / "deploy" / "opennasr-update"
    loader = SourceFileLoader("opennasr_update", str(script))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.mark.parametrize("failure", [None, "signature", "hash"])
def test_verifies_signature_and_wheels(updater, tmp_path, monkeypatch, failure):
    tag = "v2.0.0"
    names = [
        "opennasr-2.0.0-py3-none-any.whl",
        "opennasr_contract-0.1.0-py3-none-any.whl",
        "opennasr_api-0.1.0-py3-none-any.whl",
    ]
    downloads = {
        "manifest.json": json.dumps(
            {
                "schema": 1,
                "version": tag,
                "repository": updater.REPOSITORY,
                "assets": {
                    name: hashlib.sha256(name.encode()).hexdigest() for name in names
                },
            }
        ).encode(),
        "manifest.json.sigstore.json": b"bundle",
        **{name: name.encode() for name in names},
    }
    verified = False

    def download(url, path):
        assert url == f"{updater.GITHUB}/releases/download/{tag}/{path.name}"
        if path.suffix == ".whl":
            assert verified
        path.write_bytes(
            b"corrupt"
            if failure == "hash" and path.name == names[0]
            else downloads[path.name]
        )

    def verify(command, *, check):
        nonlocal verified
        assert check and command[:2] == ["cosign", "verify-blob"]
        assert (
            f"{updater.GITHUB}/.github/workflows/release.yml@refs/tags/{tag}" in command
        )
        assert updater.ISSUER in command
        if failure == "signature":
            raise subprocess.CalledProcessError(1, command)
        verified = True

    monkeypatch.setattr(updater, "download", download)
    monkeypatch.setattr(updater.subprocess, "run", verify)
    if failure == "signature":
        with pytest.raises(subprocess.CalledProcessError):
            updater.verified_wheels(tag, "api", tmp_path)
        assert not list(tmp_path.glob("*.whl"))
    elif failure == "hash":
        with pytest.raises(ValueError, match="SHA-256 mismatch"):
            updater.verified_wheels(tag, "api", tmp_path)
    else:
        requirements = updater.verified_wheels(tag, "api", tmp_path)
        assert [requirement.split(" @ ")[0] for requirement in requirements] == [
            "opennasr",
            "opennasr_contract[s3]",
            "opennasr_api",
        ]


def test_switch_restores_previous_executable_after_failed_readiness(
    updater, tmp_path, monkeypatch
):
    override = tmp_path / "systemd" / "50-signed-release.conf"
    previous = tmp_path / "previous-exec-start"
    unit = "openNASR-api.service"
    observed = []

    def activate(role, name, ready_url):
        observed.append(updater.read_override(override))
        if observed[-1] == "unhealthy":
            raise RuntimeError("not ready")

    monkeypatch.setattr(updater, "activate", activate)
    updater.switch("api", unit, "ready", override, previous, "first")
    assert previous.read_text() == ""

    with pytest.raises(RuntimeError, match="not ready"):
        updater.switch("api", unit, "ready", override, previous, "unhealthy")
    assert observed == ["first", "unhealthy", "first"]
    assert override.read_text() == "first"
    assert previous.read_text() == ""

    updater.switch("api", unit, "ready", override, previous, previous.read_text())
    assert not override.exists()
    assert previous.read_text() == "first"
