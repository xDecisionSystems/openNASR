# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow Semantic Versioning.

## [Unreleased]

## [1.4.0] - Unreleased

### Added

- Rich ATC, radar, weather, flight-service-station, and location-identifier
  repositories using verified FAA composite keys and child collections.

## [1.3.0] - Unreleased

### Added

- Rich coded-departure, departure-procedure, preferred-route, and STAR
  repositories with composite-key lookup and FAA sequence ordering.

## [1.2.0] - Unreleased

### Added

- Rich airway, holding-pattern, communication-outlet, and frequency APIs with
  ordered airway/remark collections and public repository exports.
- Verified composite-key links from airway points, holding patterns, and
  communication outlets to their matching fix or navaid records.
- Synthetic navigation-network fixtures and coverage checks for both supported
  FAA schema generations.

### Fixed

- Frequency lookups now require their complete serviced-facility context;
  communication and frequency links never rely on display names alone.

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
