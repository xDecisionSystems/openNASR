"""Cycle-cache configuration tests."""

from pathlib import Path

from openNASR import cycles
from openNASR.cycles import CycleManager, resolve_cache_dir


def test_explicit_cache_directory_has_highest_precedence(monkeypatch, tmp_path):
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("OPENNASR_CACHE_DIR", str(tmp_path / "environment"))
    monkeypatch.setattr(cycles, "user_cache_dir", lambda _: str(tmp_path / "default"))

    assert resolve_cache_dir(explicit) == explicit
    assert CycleManager(explicit).cache_dir == explicit


def test_environment_cache_directory_overrides_platform_default(monkeypatch, tmp_path):
    configured = tmp_path / "environment"
    monkeypatch.setenv("OPENNASR_CACHE_DIR", str(configured))
    monkeypatch.setattr(cycles, "user_cache_dir", lambda _: str(tmp_path / "default"))

    assert resolve_cache_dir() == configured


def test_platform_cache_directory_is_used_without_overrides(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENNASR_CACHE_DIR", raising=False)
    default = tmp_path / "platform-default"
    monkeypatch.setattr(cycles, "user_cache_dir", lambda _: str(default))

    assert resolve_cache_dir() == Path(default)
