# Phase 5 automotive analytics

An empty configuration history is a factual insufficient result with zero contributors and
`insufficient_same_configuration_sessions`, rather than an API failure or a claim of mixed
configuration. The browser displays this limitation and the zero session/pull counts explicitly.

## Pipeline and source of truth

Canonical telemetry is the measurement source of truth. Phase 2 supplies persisted pulls; Phase 3
supplies factual event references; Phase 4 capability and acquisition-quality metadata govern metric
availability. Analytics never redetect events or replace missing metrics with zero.

The pipeline separates selection, common-window comparability, RPM/time normalization, metric
extraction, robust aggregation, sufficiency, immutable persistence, API contracts, and presentation.
Default requests are bounded to 20 pulls and 500,000 observations. Client configuration consists only
of validated allowlisted fields; executable SQL, Python, and formula input is forbidden.

## Metrics and normalization

Pull profiles cover duration/RPM, speed, throttle, boost, IAT, coolant, oil, high-pressure fuel,
acceleration intervals, events, and quality when signals exist. Values retain canonical units: m/s,
Pa, K, RPM, and percent. Curves use configurable half-open RPM bins (250 RPM default), minimum three
samples, and a maximum one-second gap. Each supported bin contains count, time coverage, median,
mean, min/max, p10/p25/p75/p90 when five samples exist, MAD, completeness, and sufficiency.

Speed intervals use linear interpolation only between consecutive samples no more than one second
apart and require both boundaries. Defaults are 60–100, 80–120, and 100–150 km/h (converted to m/s).
Controlled, legal data collection remains required; this is not street-racing timing.

## Comparability and sufficiency

Comparability dimensions and weights are RPM overlap .35, duration .15, throttle .20, initial thermal
context .10, and quality .20. The score is a transparent heuristic, not a calibrated probability.
Vehicle and configuration must match; common range must span 750 RPM; completeness must be .70.
Rejection reasons are returned.

Sufficiency is `sufficient`, `limited`, `insufficient`, or `not_applicable`. Repeatability requires at
least two comparable pulls. Baselines require three eligible sessions under one configuration.
Correlations require five comparable observations and are labelled observed, non-causal associations.
Trends preserve configuration segments. Before/after views state observed differences only.

Before/after selection exposes separate before and after configuration controls. Each side queries
up to 20 persisted pulls under its selected configuration instead of filtering the general preview
catalog. The pull-list API accepts an optional `configuration_id` filter; omitting it preserves the
existing bounded ordering and response contract. This is a backward-compatible query addition,
with no database schema, analytics algorithm version or configuration-hash change.

## Robust statistics and provenance

Median is the midpoint; MAD is median absolute deviation; IQR is p75 minus p25; sample CV is sample
standard deviation over absolute mean. Percentiles interpolate sorted values. Spearman uses average
ranks for ties. Results contain source selection, counts, definitions, units, normalization, common
range, quality, completeness, version/hash, baseline source, warnings, and evidence quality.

Identical identities are reusable; explicit recompute produces a new immutable run.

**Observed association is not root-cause diagnosis.** Phase 5 provides no repair recommendation,
ECU/tuning control, causal inference, BMW proprietary signal invention, ML, MCP, agents, or RAG.

## Retrospective calculation identity

Algorithm 1.1.0 / calculation configuration `phase5-analytics-v1.1` corrects common-RPM
window clipping, event-time endpoints, interval continuity, per-pull historical bin coverage,
paired correlations and configuration-specific trend sufficiency. Old immutable results are
retained; their identities cannot be reused for the new algorithm. Fingerprints include
canonical measurements, event references, quality, context and semantic selectors (including
trend metric and before/after roles). Advisory locks serialize concurrent identical requests.

Session summaries use persisted telemetry, segments, categorized events and capability reports,
including sessions without detected pulls. Empty history returns explicit insufficiency.
Baseline bins report contributing pulls and sessions; across-pull median/MAD and percentiles
do not bridge separate sessions. Trends require at least three eligible sessions in each
configuration segment. Incomparable pulls do not produce pooled associations.

## Retrospective metric and presentation completeness

Observed acceleration is the difference between adjacent measured speeds divided by elapsed time,
using only positive intervals within the configured gap bound. Its RPM bins retain m/s² units;
no missing speed is replaced by zero. Thermal rate is endpoint delta divided by elapsed time only
with complete, continuous signal coverage. Repeated-pull normalized metrics use the common RPM
window, while thermal start/end and between-pull recovery use actual pull endpoints. Recovery
threshold timing remains explicitly unavailable because the selected pull inputs do not include
measurements between pulls; endpoint delta and elapsed time are factual, not interpolated recovery.

Speed intervals are allowlisted typed configuration: one to five finite increasing pairs in
0–300 km/h, defaulting to the original three intervals. Changing intervals changes the configuration
hash. This is an additive OpenAPI request field; omitted fields preserve the original defaults.

Comparison charts use common RPM/value axes, separate lines across insufficient bins, measured
coverage, distinct dash patterns, accessible value tables and canonical Phase 3 event markers.
Markers reference persisted event IDs and the nearest observed RPM at event start; analytics do
not redetect events. Boost, IAT, fuel, speed, throttle and observed acceleration are selectable.
