"""Object storage for published cycles.

Keys are immutable: writing a key that already holds different bytes is an
error, and writing the same bytes again is a no-op. That is what makes
re-running the archiver after a partial failure safe.
"""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
from pathlib import Path
from shutil import copyfileobj
import tempfile
from typing import Protocol


class ImmutableKeyError(RuntimeError):
    """Raised when a key already exists with different content."""


class Bucket(Protocol):
    def exists(self, key: str) -> bool: ...

    def put_file(self, key: str, path: Path, sha256: str) -> None: ...

    def put_bytes(self, key: str, data: bytes) -> None: ...

    def get_bytes(self, key: str) -> bytes: ...

    def get_file(self, key: str, destination: Path) -> None: ...

    def list_keys(self, prefix: str = "") -> Iterator[str]: ...


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LocalBucket:
    """A bucket in a local directory, used for tests and local runs."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError(f"key escapes the bucket: {key!r}")
        return path

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def put_file(self, key: str, path: Path, sha256: str) -> None:
        if _sha256(path) != sha256:
            raise ValueError(f"{path} does not match its stated sha256")
        destination = self._path(key)
        if destination.is_file():
            if _sha256(destination) != sha256:
                raise ImmutableKeyError(f"{key} already exists with different content")
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as out:
            temporary = Path(out.name)
            with path.open("rb") as source:
                copyfileobj(source, out, 1024 * 1024)
        temporary.replace(destination)

    def put_bytes(self, key: str, data: bytes) -> None:
        destination = self._path(key)
        if destination.is_file():
            if destination.read_bytes() != data:
                raise ImmutableKeyError(f"{key} already exists with different content")
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as out:
            temporary = Path(out.name)
            out.write(data)
        temporary.replace(destination)

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def get_file(self, key: str, destination: Path) -> None:
        with self._path(key).open("rb") as source, destination.open("wb") as out:
            copyfileobj(source, out, 1024 * 1024)

    def list_keys(self, prefix: str = "") -> Iterator[str]:
        root = self.root.resolve()
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.name.startswith("tmp"):
                key = path.relative_to(root).as_posix()
                if key.startswith(prefix):
                    yield key
