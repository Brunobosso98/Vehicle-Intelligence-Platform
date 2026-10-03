# ADR 0016: Deterministic, immutable automotive analytics

## Status

Accepted.

## Decision

Phase 5 uses a layered pure-statistics engine above canonical telemetry, pulls, events, acquisition
quality, and vehicle configuration. A generic `analytics_runs` table stores typed JSON results plus
an analytics type, algorithm/version, deterministic configuration hash, source fingerprint, input
summary, status, warnings, vehicle/configuration identity, and timestamp. Completed results are
immutable; an explicit recompute creates another auditable run. Identical default requests reuse the
latest compatible result.

Comparability is transparent rather than probabilistic: RPM overlap, duration, throttle, initial
thermal context, and quality use documented weights of 35%, 15%, 20%, 10%, and 20%. A comparison
also requires the same vehicle/configuration, at least 750 RPM overlap, and 70% completeness. Only
the common half-open RPM window is normalized, in configurable 250 RPM bins by default. Bins need
three samples and never bridge a gap over one second.

Historical baselines require three same-configuration sessions and compatible algorithm semantics.
Poor-quality pulls are excluded visibly. Rebuilds create a new timestamped result; configurations
form separate trend segments. Robust median, MAD, IQR, CV, percentile, and guarded Spearman helpers
are centralized and deterministic.

Analytics describe observed measurements and associations. They do not infer causes, diagnose
components, recommend repairs, execute arbitrary expressions, or use ML. Those capabilities remain
deferred.

## Consequences

Results are reproducible and future tool-ready without introducing Phase 6 infrastructure. JSONB
keeps related evidence atomic while indexed identity and vehicle/configuration columns support
bounded lookup. Algorithm changes require a new version and never reinterpret prior results.
