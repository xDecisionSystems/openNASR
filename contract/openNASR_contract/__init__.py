"""The bucket contract between the openNASR archiver and the API.

This package is the only coupling between the two: the key layout of the S3
bucket and the manifest that marks a build as validated. It has no
dependencies beyond the standard library.
"""

from .keys import (
    LAYOUT_VERSION,
    BucketKeyError,
    BuildKeys,
    build_keys,
    parse_manifest_key,
)
from .manifest import (
    ArtifactRef,
    Manifest,
    ManifestError,
)

__all__ = [
    "LAYOUT_VERSION",
    "ArtifactRef",
    "BucketKeyError",
    "BuildKeys",
    "Manifest",
    "ManifestError",
    "build_keys",
    "parse_manifest_key",
]
