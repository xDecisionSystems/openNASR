# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow Semantic Versioning.

## [Unreleased]

## [1.1.0] - Unreleased

### Added

- Airport-linked `ClassAirspace` and `MilitaryOperation` records, repositories,
  and airport relationships using the verified `(SITE_NO, SITE_TYPE_CODE)` key.
- Lossless FAA records with shared typed converters and contextual conversion errors.
- Cycle discovery, caching, archive validation, and update-status handling.
- Airport, Fix, and Navaid repositories with normalized lookups and typed fields.
- ARTCC boundary mappings, multipolygon preservation, and coordinate validation.
- Public API reference, migration guide, and README example validation.

### Changed

- Designated `1.0.0` as the first supported release while retaining the
  pre-release package version until all release blockers are resolved.
- Airport plotting returns its `Figure` and `Axes` and no longer closes all figures
  by default.
- Coordinate helpers expose explicit latitude/longitude ordering and nautical-mile
  projection distances.

### Fixed

- Empty fields and leading-zero identifiers remain unchanged in raw records.
- Ambiguous lookups preserve candidate records without printing to stdout.
- Optional plotting dependencies no longer prevent core package access.
