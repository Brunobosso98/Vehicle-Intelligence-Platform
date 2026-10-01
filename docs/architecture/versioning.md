# Versioning and compatibility

Application uses SemVer; foundation is 0.1.0. /version carries safe version, Git SHA,
build timestamp and environment. Build timestamps are timezone-aware ISO8601, UTC internally.
Health/version paths are intentionally unprefixed operational endpoints. Future domain REST
routes use /api/v1. Changing a required field, removing fields or narrowing allowed values is
breaking; review a versioned transition and ADR when significant. Additive optional fields are
normally compatible but still require contract regeneration and consumer tests.

Future event names follow `telemetry.sample.v1`, `vehicle.configuration.v1`, `diagnostic.event.v1`.
These names are conventions, not implemented schemas. Never edit generated artifacts manually.
API CI runs deterministic regeneration to detect drift. Breaking changes require explicit PR rationale,
new major contract boundary where needed and migration/consumer compatibility tests.
