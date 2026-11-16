"""S3 (or S3-compatible, e.g. MinIO) bucket. Requires the ``s3`` extra (boto3)."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
from pathlib import Path
from typing import Any

from .bucket import ImmutableKeyError


def _not_found(error: Exception) -> bool:
    response = getattr(error, "response", {}) or {}
    code = str(response.get("Error", {}).get("Code", ""))
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in {"404", "NoSuchKey", "NotFound"} or status == 404


class S3Bucket:
    """Immutable-key storage in one S3 bucket.

    A file's SHA-256 is stored as object metadata so a re-upload of identical
    content is recognised without downloading it.
    """

    def __init__(
        self,
        bucket: str,
        *,
        prefix: str = "",
        client: Any | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        if client is None:
            import boto3  # optional dependency

            client = boto3.client("s3", endpoint_url=endpoint_url)
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def _head(self, key: str) -> dict | None:
        try:
            return self._client.head_object(Bucket=self._bucket, Key=self._key(key))
        except Exception as error:
            if _not_found(error):
                return None
            raise

    def exists(self, key: str) -> bool:
        return self._head(key) is not None

    def put_file(self, key: str, path: Path, sha256: str) -> None:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != sha256:
            raise ValueError(f"{path} does not match its stated sha256")
        head = self._head(key)
        if head is not None:
            stored = (head.get("Metadata") or {}).get("sha256")
            if stored != sha256:
                raise ImmutableKeyError(f"{key} already exists with different content")
            return
        self._client.upload_file(
            str(path),
            self._bucket,
            self._key(key),
            ExtraArgs={"Metadata": {"sha256": sha256}},
        )

    def put_bytes(self, key: str, data: bytes) -> None:
        sha256 = hashlib.sha256(data).hexdigest()
        head = self._head(key)
        if head is not None:
            if (head.get("Metadata") or {}).get("sha256") != sha256:
                raise ImmutableKeyError(f"{key} already exists with different content")
            return
        self._client.put_object(
            Bucket=self._bucket,
            Key=self._key(key),
            Body=data,
            Metadata={"sha256": sha256},
        )

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=self._key(key))
        return response["Body"].read()

    def get_file(self, key: str, destination: Path) -> None:
        self._client.download_file(self._bucket, self._key(key), str(destination))

    def list_keys(self, prefix: str = "") -> Iterator[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._key(prefix)):
            for item in page.get("Contents", []):
                yield item["Key"][len(self._prefix) :]
