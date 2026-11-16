"""``S3Bucket`` against an in-memory stand-in for the boto3 client."""

import hashlib
import io

import pytest

from openNASR_contract import ImmutableKeyError
from openNASR_contract.s3 import S3Bucket


class _NotFound(Exception):
    response = {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}}


class FakeS3:
    """Just enough of the boto3 S3 client API."""

    def __init__(self):
        self.objects: dict[tuple[str, str], tuple[bytes, dict]] = {}
        self.uploads = 0

    def head_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise _NotFound()
        return {"Metadata": self.objects[(Bucket, Key)][1]}

    def put_object(self, Bucket, Key, Body, Metadata):
        self.objects[(Bucket, Key)] = (Body, Metadata)

    def upload_file(self, filename, bucket, key, ExtraArgs):
        self.uploads += 1
        with open(filename, "rb") as handle:
            self.objects[(bucket, key)] = (handle.read(), ExtraArgs["Metadata"])

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)][0])}

    def download_file(self, bucket, key, filename):
        with open(filename, "wb") as handle:
            handle.write(self.objects[(bucket, key)][0])

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        outer = self

        class Paginator:
            def paginate(self, Bucket, Prefix):
                keys = sorted(k for b, k in outer.objects if b == Bucket)
                yield {"Contents": [{"Key": k} for k in keys if k.startswith(Prefix)]}

        return Paginator()


@pytest.fixture
def bucket():
    return S3Bucket("nasr", prefix="prod", client=FakeS3())


def test_bytes_round_trip_under_the_prefix(bucket):
    bucket.put_bytes("2026/a.json", b"hello")

    assert bucket.exists("2026/a.json")
    assert bucket.get_bytes("2026/a.json") == b"hello"
    assert list(bucket.list_keys("2026/")) == ["2026/a.json"]
    assert ("nasr", "prod/2026/a.json") in bucket._client.objects


def test_identical_bytes_are_a_no_op_and_different_bytes_are_refused(bucket):
    bucket.put_bytes("k", b"one")
    bucket.put_bytes("k", b"one")

    with pytest.raises(ImmutableKeyError):
        bucket.put_bytes("k", b"two")


def test_files_are_uploaded_once_and_verified(bucket, tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"payload")
    sha = hashlib.sha256(b"payload").hexdigest()

    bucket.put_file("2026/f.bin", path, sha)
    bucket.put_file("2026/f.bin", path, sha)  # already stored: no second upload

    assert bucket._client.uploads == 1
    destination = tmp_path / "copy.bin"
    bucket.get_file("2026/f.bin", destination)
    assert destination.read_bytes() == b"payload"

    other = tmp_path / "g.bin"
    other.write_bytes(b"changed")
    with pytest.raises(ImmutableKeyError):
        bucket.put_file("2026/f.bin", other, hashlib.sha256(b"changed").hexdigest())
    with pytest.raises(ValueError, match="does not match"):
        bucket.put_file("2026/h.bin", other, sha)


def test_other_errors_are_not_mistaken_for_missing_keys(bucket):
    class Broken(FakeS3):
        def head_object(self, Bucket, Key):
            raise RuntimeError("connection reset")

    broken = S3Bucket("nasr", client=Broken())
    with pytest.raises(RuntimeError, match="connection reset"):
        broken.exists("k")


def test_env_file_parsing_ignores_comments_and_strips_quotes(tmp_path):
    from openNASR_contract.s3 import load_env_file

    path = tmp_path / ".env"
    path.write_text("# c\n\nA=1\nB='two'\nC=\"three\"\nnoequals\n", encoding="utf-8")

    assert load_env_file(path) == {"A": "1", "B": "two", "C": "three"}


def test_from_env_names_the_missing_variable():
    with pytest.raises(KeyError, match="OPENNASR_S3_BUCKET"):
        S3Bucket.from_env({}, "API")
    environ = {
        "OPENNASR_S3_BUCKET": "b",
        "OPENNASR_S3_ENDPOINT_URL": "https://example.invalid",
    }
    with pytest.raises(KeyError, match="OPENNASR_ARCHIVER_S3_ACCESS_KEY_ID"):
        S3Bucket.from_env(environ, "ARCHIVER")
