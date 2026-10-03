# Phase 5 — Automotive Analytics

Implement Phase 5 — Automotive Analytics for the Vehicle Intelligence Platform / N55 Intelligence Lab.

## Repository and branch

Repository: Brunobosso98/Vehicle-Intelligence-Platform

Work only on the existing branch:

codex/phase-5-automotive-analytics

This branch was created directly from the Phase 4 merged main baseline:

341ca6e8eb5f0383edefe191452285f5539d2b6d

Do not work directly on main.
Do not create another Phase 5 branch.
Do not implement Phase 6 MCP, Phase 7 agents, Phase 8 RAG, Phase 9 ML, or later phases.

Treat this as a production-grade engineering milestone, not a demo.

---

## 1. Product definition

Phase 5 transforms canonical telemetry, sessions, pulls, events, acquisition provenance, recipes, vehicle configurations, and modifications into deterministic automotive analytics.

The target progression is:

```
Canonical telemetry
    ↓
Driving sessions
    ↓
Segments and pulls
    ↓
Factual events
    ↓
Comparable operating windows
    ↓
Normalized pull analytics
    ↓
Repeated-pull analytics
    ↓
Session analytics
    ↓
Cross-session analytics
    ↓
Vehicle/configuration baselines
    ↓
Modification before/after analytics
    ↓
Longitudinal trends
```

Phase 5 answers questions such as:

- How did comparable pulls differ?
- How repeatable was the vehicle within a session?
- Did boost behavior change as IAT increased?
- Was fuel-pressure behavior stable across the same RPM range?
- Did normalized acceleration change across repeated pulls?
- How does this session compare with prior sessions under the same vehicle configuration?
- Did behavior change after a recorded modification?
- What is this vehicle's own historical envelope for a metric under comparable conditions?
- Is there enough comparable history to make a meaningful statement?

Phase 5 must NOT answer:

- Which component is broken?
- What repair should be performed?
- What caused an anomaly?
- What should be tuned in the ECU?
- What modification should the user buy?

Those belong to later reasoning, knowledge, or diagnostic phases.

---

## 2. First verify git, baseline, remote, and publishing ability

Before substantial implementation run:

```
git status
git branch --show-current
git log --oneline -10
git remote -v
git merge-base HEAD 341ca6e8eb5f0383edefe191452285f5539d2b6d
```

Current branch must be:

codex/phase-5-automotive-analytics

It must descend from:

341ca6e8eb5f0383edefe191452285f5539d2b6d

Verify the remote branch and push ability:

```
git ls-remote origin refs/heads/codex/phase-5-automotive-analytics
git push --dry-run origin HEAD:codex/phase-5-automotive-analytics
```

If origin is missing or wrong, repair it.

If authentication prevents push, fix it before doing substantial work.

Do not complete the phase in an unpublished workspace.

---

## 3. Read the current repository before implementation

Read and understand:

- root AGENTS.md;
- nested AGENTS.md files;
- README;
- roadmap;
- architecture docs for Phases 1–4;
- relevant ADRs;
- testing strategy;
- security docs;
- observability docs;
- telemetry domain;
- Vehicle, VehicleConfiguration and Modification models;
- DrivingSession;
- Phase 2 segment/pull models and comparability logic;
- Phase 3 DetectedEvent and baseline/evidence contracts;
- Phase 4 acquisition sessions, recipes, capability reports and quality metadata;
- current API;
- generated OpenAPI/TypeScript types;
- current frontend session/pull/event UI;
- Alembic migrations and current head;
- Makefile;
- CI;
- Security workflow;
- canonical full validation;
- existing acceptance scripts.

Preserve completed Phase 0–4 behavior.

Reuse existing alignment, pull, event, quality, vehicle configuration, and acquisition provenance logic where appropriate.

Do not create incompatible parallel definitions of concepts that already exist.

---

## 4. Update phase context

After implementation, repository context must accurately state:

- Phase 0 complete;
- Phase 1 complete;
- Phase 2 complete;
- Phase 3 complete;
- Phase 4 complete;
- Phase 5 current/complete depending validation;
- Phase 6+ planned.

Do not erase historical evidence.

---

## 5. Safety and interpretation boundary

Phase 5 performs deterministic analytics.

It may state measured or derived relationships.

Allowed:

“Across 4 comparable pulls, median IAT increased by 13.2 C and normalized acceleration decreased by 3.7%.”

Allowed:

“Boost in the 5000–5500 rpm bin was 4.2% lower than the same-session median envelope.”

Not allowed:

“Heat soak caused the performance loss.”

Not allowed:

“The intercooler is inadequate.”

Not allowed:

“The turbo is failing.”

Not allowed:

“The HPFP needs replacement.”

Correlation, co-movement, and change are not physical-cause proof.

UI, API, docs, and evidence contracts must preserve this distinction.

---

## 6. Phase 5 architecture

Create a coherent analytics layer on top of canonical persisted data.

Conceptually:

```
Telemetry + Pulls + Events + Configuration + Acquisition Quality
        ↓
Comparable Window Builder
        ↓
RPM / speed / time normalization
        ↓
Metric extractors
        ↓
Pull Analytics
        ↓
Repeated Pull Analytics
        ↓
Session Analytics
        ↓
Cross-session Comparator
        ↓
Historical Baseline Builder
        ↓
Modification / Configuration Comparator
        ↓
Trend Analytics
        ↓
Persisted versioned analytics results
        ↓
Typed API + Analytics Workspace
```

Keep HTTP routes thin.

Separate:

- data selection;
- comparability;
- normalization;
- metric computation;
- aggregation;
- uncertainty/data sufficiency;
- persistence;
- presentation.

---

## 7. First-class analytics run/versioning

Introduce a versioned analytics execution identity if needed.

Concepts should include:

- analytics type;
- algorithm name;
- algorithm version;
- configuration;
- deterministic configuration hash;
- input vehicle/configuration;
- input session(s)/pull(s);
- input data-quality summary;
- generated_at;
- result status;
- warnings;
- evidence/provenance.

Identical runs with the same inputs, algorithm version and config should be reusable/idempotent.

Changing algorithm/config must remain auditable.

Do not silently mutate historical analytics.

---

## 8. Analytics result types

Implement structured result models rather than only prose.

At minimum support concepts equivalent to:

- PullAnalytics;
- PullComparison;
- RepeatedPullAnalysis;
- SessionAnalytics;
- VehicleBaseline;
- CrossSessionComparison;
- ModificationComparison;
- TrendSeries.

Use repository conventions and avoid unnecessary table explosion.

Some results may share a generic versioned analysis/run table with typed payloads if that is cleaner and queryable.

Document the decision.

---

## 9. Evidence-first analytics contract

Every derived result must expose:

- source IDs or reproducible selection criteria;
- metric definition;
- units;
- normalization method;
- number of observations;
- number of pulls/sessions;
- comparable range;
- data-quality flags;
- completeness;
- calculation version;
- baseline source;
- confidence/evidence quality where applicable.

Do not return unexplained scalar scores.

---

## 10. Data sufficiency states

Use explicit states such as:

- sufficient;
- limited;
- insufficient;
- not_applicable.

Absence of enough history must not be converted into a weak conclusion.

Examples:

- only one pull available → no repeatability conclusion;
- two historical sessions with mismatched configuration → no same-configuration trend;
- no overlapping RPM window → no pull comparison;
- poor signal coverage → relevant metric unavailable.

---

## 11. Reuse Phase 2 comparability but extend it carefully

Phase 3 currently has same-session pull comparability based on duration and overlapping RPM span.

Phase 5 should centralize and extend comparability as needed.

Potential dimensions:

- same vehicle;
- same VehicleConfiguration;
- overlapping RPM window;
- duration similarity;
- throttle/load similarity;
- speed range;
- gear if reliable gear information later exists;
- initial thermal state;
- acquisition quality;
- signal availability.

Do not compare arbitrary pulls just because they belong to the same vehicle.

---

## 12. Comparability score and dimensions

Represent comparability transparently.

Example result:

```
overall: 0.84
rpm_overlap: 0.96
duration_similarity: 0.88
throttle_similarity: 0.90
thermal_similarity: 0.63
quality_similarity: 0.94
```

Weights must be documented and versioned.

Do not pretend the score is a calibrated probability.

Expose reasons for rejection.

---

## 13. Comparable operating windows

Create a reusable abstraction for comparing only overlapping portions of pulls/sessions.

A comparison must know:

- common RPM range;
- common speed range if relevant;
- start/end;
- minimum samples;
- coverage;
- gaps;
- interpolation limits.

Never compare Pull A at 3000 rpm to Pull B only observed at 5200 rpm and call them equivalent.

---

## 14. RPM-normalized analytics

Implement deterministic RPM binning.

Provide a default bin size, for example 250 rpm, but make it configuration-driven and versioned.

Potential bins:

- 3000–3250;
- 3250–3500;
- etc.

For each bin calculate metrics only when minimum data-quality and coverage criteria are met.

Do not bridge large telemetry gaps.

---

## 15. Bin aggregation

For appropriate signals compute:

- count;
- time coverage;
- median;
- mean where meaningful;
- minimum;
- maximum;
- p10/p25/p75/p90 where sample size supports it;
- MAD;
- completeness.

Prefer robust statistics for comparisons.

Do not produce percentiles from trivially tiny samples without marking them insufficient.

---

## 16. Pull Analytics Engine

For each pull derive a structured analytics profile.

Include where signals exist:

- RPM range;
- speed range;
- duration;
- throttle/load profile;
- boost profile;
- IAT profile;
- coolant temperature profile;
- oil temperature profile;
- high-pressure fuel profile;
- acceleration profile;
- relevant Phase 3 events;
- quality summary.

Metrics must preserve null when unsupported.

---

## 17. Boost analytics

For boost where available compute factual metrics such as:

- peak boost;
- median boost;
- average boost;
- boost by RPM bin;
- variability within bin;
- rise behavior;
- sustained drop/overshoot event references;
- pull-to-pull variation;
- historical envelope position.

Do not infer boost leak, wastegate failure, tune quality, or turbo condition.

---

## 18. Thermal analytics

For IAT/oil/coolant where available compute:

- start temperature;
- end temperature;
- min/max;
- within-pull delta;
- rate of increase;
- between-pull recovery;
- time-to-recovery threshold when definable;
- repeated-pull accumulation;
- normalized temperature by RPM/time window;
- thermal context for performance metrics.

Do not label this heat soak automatically.

Use factual names such as:

- IAT accumulation;
- thermal accumulation;
- recovery behavior;
- thermal delta.

---

## 19. Repeated-pull thermal behavior

For ordered comparable pulls in the same session compute:

- starting IAT sequence;
- ending IAT sequence;
- IAT delta per pull;
- median increase between pull starts;
- recovery between pulls;
- oil/coolant progression;
- count of thermal events from Phase 3.

This should support views such as:

```
Pull 1 start IAT 39 C
Pull 2 start IAT 45 C
Pull 3 start IAT 52 C
Pull 4 start IAT 58 C
```

No causal conclusion.

---

## 20. Fuel-system analytics

For high-pressure fuel where available compute:

- start pressure;
- minimum;
- median;
- pressure by RPM bin;
- variation;
- repeatability;
- drop event references;
- comparison to same-session and historical envelope.

Only compare target/requested vs actual if both are genuinely present.

Do not invent requested rail pressure.

Do not diagnose HPFP failure.

---

## 21. Acceleration/performance analytics

Use speed and timestamps to compute factual acceleration/performance intervals.

Support configurable intervals such as:

- 60–100 km/h;
- 80–120 km/h;
- 100–150 km/h;

only when the data actually spans the requested interval.

Also support:

- elapsed time across common RPM range;
- speed gain per second;
- acceleration slope where mathematically appropriate;
- normalized acceleration by RPM bin.

Do not brand the feature as street-racing timing.

Documentation must keep controlled/legal testing language from Phase 4.

---

## 22. Interval quality gates

Performance intervals require strict data-quality criteria.

Reject/mark limited when:

- speed sampling is too sparse;
- large gaps exist;
- interval endpoints require excessive extrapolation;
- observed_at timing is unreliable;
- the session does not span the full range.

If interpolation is used to estimate boundary crossing time:

- document it;
- cap maximum interpolation gap;
- test it;
- expose the method.

---

## 23. Pull-to-pull comparison

Implement comparison of 2–3 or more pulls.

Output should include:

- comparability dimensions;
- shared RPM window;
- metric deltas;
- percent deltas;
- per-bin curves;
- data-quality limitations;
- event references.

Do not produce “winner”, “best pull”, or subjective score.

Factual ordering such as fastest measured interval is acceptable as a raw measurement, but avoid an overall evaluative verdict.

---

## 24. Repeatability / consistency analytics

For multiple comparable pulls compute repeatability using appropriate robust metrics.

Potential measures:

- median;
- MAD;
- coefficient of variation where denominator/use is valid;
- interquartile range;
- relative spread.

Example:

```
Boost consistency: MAD 1.8%
HPFP consistency: MAD 1.1%
Acceleration interval spread: 0.12 s
```

Document formulas.

Do not create a vague “vehicle health score”.

---

## 25. Repeated-pull performance sequence

Analyze ordered pulls within a session.

For each pull derive a row such as:

- index/order;
- start IAT;
- end IAT;
- median boost in common RPM range;
- HPFP minimum;
- normalized acceleration;
- throttle coverage;
- event count.

Then calculate trends across the sequence.

Example factual output:

“Across 4 comparable pulls, start IAT rose 18 C while common-window acceleration time increased 4.1%.”

Do not assert causality.

---

## 26. Correlation analysis — conservative and explicit

Support limited deterministic association metrics when useful.

Potential examples:

- IAT vs normalized acceleration;
- IAT vs boost;
- boost vs acceleration;
- fuel pressure vs load.

Requirements:

- minimum sample/pull count;
- same comparable context;
- no causal wording;
- clearly identify correlation type;
- report sample size;
- report if evidence is too weak.

Prefer Spearman rank correlation for small monotonic relationships where justified.

Pearson may be available when assumptions are appropriate and documented.

Do not automatically label correlations as significant without appropriate sample size/statistical treatment.

---

## 27. Avoid fake statistics

Do not output:

“Correlation: 0.91”

from three data points as strong evidence.

Use minimum sample thresholds and labels such as:

- insufficient;
- exploratory;
- supported.

Do not implement p-value theater without adequate design.

---

## 28. Session Analytics

Create a structured session summary including:

- duration;
- telemetry observations;
- quality;
- segment counts;
- pull count;
- comparable pull groups;
- event count/by category;
- signal coverage;
- boost summary;
- thermal summary;
- fuel summary;
- acceleration intervals;
- repeatability where available;
- post-log capability report from Phase 4.

Keep unsupported fields null/absent with explicit limitation.

---

## 29. Comparable pull groups

Within a session, group pulls that are actually comparable.

Do not force one comparison group if the session contains fundamentally different pulls.

Persist or reproducibly derive:

- group members;
- comparability criteria;
- shared RPM range;
- configuration hash/version.

---

## 30. Cross-session comparison

Compare sessions only when:

- same vehicle;
- compatible/same configuration unless explicitly comparing configurations;
- sufficient signal overlap;
- sufficient pull comparability;
- acceptable data quality.

Output:

- number of comparable pulls per session;
- common RPM window;
- aggregate boost profile;
- thermal behavior;
- fuel behavior;
- acceleration metrics;
- event rates;
- quality limitations.

---

## 31. VehicleConfiguration is mandatory context

Do not mix telemetry from incompatible configurations in a historical baseline.

Examples of configuration changes that should normally create separate contexts:

- Stage/tune change;
- intercooler;
- intake;
- downpipe;
- fuel system changes;
- turbo changes.

Use the existing VehicleConfiguration/Modification model rather than creating hidden ad-hoc labels.

---

## 32. Historical vehicle baseline

Implement a baseline for a vehicle under a specific configuration.

A VehicleBaseline should represent the vehicle’s own observed history, not a generic BMW/N55 truth.

Potential baseline dimensions:

- metric;
- signal;
- RPM bin;
- comparable operating context;
- configuration;
- sample count;
- session count;
- pull count;
- median;
- MAD;
- percentile envelope;
- first/last included timestamp;
- calculation version.

---

## 33. Minimum baseline evidence

Do not create a strong historical baseline from trivial data.

Use explicit minimum thresholds.

For example, baseline states may depend on:

- minimum number of comparable pulls;
- minimum sessions;
- sufficient temporal coverage;
- signal quality.

The exact thresholds must be centralized, typed, documented, and tested.

If insufficient:

“insufficient comparable history”

rather than fabricating a baseline.

---

## 34. Historical baseline provenance

Persist/reproduce which:

- sessions;
- pulls;
- vehicle configuration;
- quality filters;
- algorithm version;
- binning configuration

contributed to the baseline.

Future agents must be able to audit the origin.

---

## 35. Baseline envelope

For sufficient history expose robust envelope metrics such as:

- median;
- p10/p90;
- p25/p75;
- MAD.

Use them to state factual relative position.

Example:

“Current boost at 5000–5250 rpm is below the historical p10 envelope for this configuration.”

Do not convert that into a component diagnosis.

---

## 36. Cross-session trend analytics

Implement longitudinal trends only when comparable history exists.

Potential series:

- boost median by RPM bin over session date;
- IAT start/end/delta;
- fuel-pressure minima;
- acceleration interval time;
- repeatability spread;
- event frequency.

Trend result must include:

- observations;
- sessions;
- configuration;
- time range;
- robust slope/change where meaningful;
- limitations.

---

## 37. Trend guardrails

Do not report meaningful trend from:

- one session;
- incompatible configurations;
- highly sparse points;
- poor quality;
- non-overlapping RPM windows.

A trend API should be capable of returning insufficient_data.

---

## 38. Modification before/after analytics

Use existing Modification and VehicleConfiguration history.

Support comparisons such as:

“before configuration A” versus “after configuration B”.

Do not infer that the modification caused all differences.

Output factual deltas with context.

Potential metrics:

- repeated-pull IAT accumulation;
- thermal recovery;
- boost profile;
- fuel-pressure profile;
- acceleration interval;
- event frequency;
- repeatability.

---

## 39. Before/after comparability

Require:

- same vehicle;
- clearly defined configuration boundary;
- adequate pull counts;
- overlapping operating ranges;
- sufficient quality.

Expose sample sizes separately for before and after.

Do not hide imbalance such as 20 pulls before vs 2 after.

---

## 40. Before/after factual language

Allowed:

“Median repeated-pull IAT delta was 8.7 C before and 4.6 C after this configuration change.”

Not allowed:

“The intercooler improved thermal efficiency by 47%”

unless the metric definition genuinely measures that engineering property, which it currently does not.

Use “observed difference”, not physical-cause certainty.

---

## 41. Foundation for Vehicle Memory / Digital Twin

Phase 5 should create the analytical foundation for future Vehicle Memory.

Do not implement an LLM memory system.

The structured timeline should be able to connect:

- vehicle;
- configurations;
- modifications;
- sessions;
- pulls;
- events;
- analytics runs;
- baselines;
- trends.

Future systems should be able to answer historically:

“what changed after configuration X?”

from structured data.

---

## 42. No hidden mutable baseline

A baseline must be versioned or reproducible.

If new sessions become eligible, a newly calculated baseline should not silently rewrite old analysis evidence in a way that makes past results unauditable.

Choose either:

- immutable baseline snapshots;
- versioned materialized baselines;
- reproducible baseline definitions tied to run timestamps.

Document the model in an ADR.

---

## 43. Analytics configuration

Centralize typed configuration such as:

- RPM bin size;
- minimum overlap;
- minimum observations per bin;
- maximum interpolation gap;
- minimum comparable pulls;
- baseline minimum pull/session counts;
- trend minimum samples;
- correlation minimum sample count;
- quality thresholds.

Use deterministic hashing.

---

## 44. Synthetic Phase 5 dataset framework

Create deterministic synthetic analytical fixtures.

Do not derive expected results from the implementation under test.

Ground truth / expected numeric bands must be defined independently where practical.

Use synthetic BMW 335i F30/N55 only as a development fixture, never authoritative vehicle calibration.

---

## 45. Required synthetic scenarios

At minimum implement:

### A. Identical repeated pulls

Expected:

- near-zero differences;
- high repeatability;
- no false trend.

### B. Progressive IAT accumulation

Expected:

- pull start/end IAT increases;
- repeated-pull thermal accumulation detected;
- no causal “heat soak” statement.

### C. Progressive boost reduction

Expected:

- normalized boost falls in specified RPM bins;
- factual sequence trend.

### D. Fuel-pressure degradation pattern

Expected:

- lower high-pressure fuel metrics in defined bins;
- no HPFP diagnosis.

### E. Slower normalized acceleration

Expected:

- controlled increase in acceleration interval/time;
- detected only in comparable windows.

### F. Noisy but unchanged vehicle

Expected:

- robust summaries remain near baseline;
- no false material trend.

### G. Different configuration

Expected:

- same-configuration baseline does not mix the new configuration automatically.

### H. Before/after configuration change

Expected:

- correct separation and factual delta.

### I. Sparse/poor-quality session

Expected:

- insufficient/limited analytics rather than fabricated conclusions.

### J. Non-overlapping pulls

Expected:

- comparison rejected.

### K. Different sample rates

Expected:

- normalized analytics remain stable within tolerance.

### L. Out-of-order/duplicate canonical input

Expected:

- deterministic results consistent with canonical Phase 1/2 semantics.

---

## 46. Golden numeric expectations

For deterministic scenarios, verify numeric analytics within explicit tolerances.

Examples:

- expected median boost delta;
- expected IAT delta;
- expected interval time;
- expected baseline median;
- expected bin-level value;
- expected trend direction/magnitude band.

Do not use only snapshot strings.

---

## 47. Analytics regression harness

Create a reusable Phase 5 acceptance/evaluation script.

Report:

- scenario count;
- pass/fail per scenario;
- numeric error per metric;
- comparison rejections expected/actual;
- false trend count;
- insufficient-data correctness;
- runtime.

Add:

make phase5-acceptance

Keep prior phase acceptance targets intact.

---

## 48. Pull comparison benchmark

Benchmark analytics over a realistically sized dataset.

Use at least:

- 100k+ telemetry observations;
- multiple sessions;
- multiple configurations;
- dozens of pulls where practical;
- historical baseline construction;
- several cross-session queries.

Report:

- telemetry/load time;
- normalization time;
- bin aggregation;
- comparison time;
- baseline build;
- trend build;
- total;
- peak memory if practical.

Do not create brittle exact latency gates.

---

## 49. Query/resource bounds

All analytics APIs must be bounded.

Define limits for:

- sessions per comparison;
- pulls per comparison;
- maximum telemetry observations loaded;
- history window;
- trend points;
- baseline contributors;
- API result rows/bins.

Avoid unbounded “analyze entire history forever” queries.

---

## 50. Database persistence

Add only necessary Phase 5 persistence.

Likely candidates:

- analytics_runs;
- analytics_results or typed summary tables;
- baseline snapshots/materializations;
- possibly normalized pull-bin summaries.

Choose based on query efficiency and auditability.

Avoid persisting every trivial intermediate array.

Use JSONB only where structured flexible evidence makes sense; use typed columns for heavily filtered/queryable dimensions.

---

## 51. Precomputation strategy

Do not recompute millions of raw observations for every dashboard refresh.

Consider persisted pull-bin summaries or materialized analytical summaries.

Document:

- when generated;
- identity/version;
- invalidation/recomputation behavior;
- relationship to source telemetry.

Do not build a complex distributed analytics platform yet.

---

## 52. No Spark/Flink requirement

Phase 5 may use Polars/DuckDB for offline analytical computation if concrete benchmarks justify them.

Do not add Spark or Flink solely for resume keywords.

If existing Python/SQL performs adequately at current scale, prefer simplicity.

Any new analytics dependency must be justified, pinned, security-scanned, and benchmarked.

---

## 53. SQL/Timescale use

Use Timescale/PostgreSQL effectively for:

- bounded filtering;
- session/pull retrieval;
- time-window selection;
- historical selection;
- persisted aggregates.

Do not force all computation into SQL if tested Python analytical code is clearer.

Document the division.

---

## 54. API — pull analytics

Provide typed bounded endpoints equivalent to:

- GET /api/v1/pulls/{id}/analytics
- POST /api/v1/analytics/pulls/compare

Exact routes should follow repository conventions.

Comparison request should explicitly identify pull IDs and analytics configuration if configurable.

---

## 55. API — repeated-pull/session analytics

Provide functionality equivalent to:

- GET/POST session analytics;
- repeated-pull analysis;
- comparable pull groups;
- session summary.

Return structured metrics, not diagnostic prose.

---

## 56. API — vehicle baseline

Provide functionality equivalent to:

- build/get baseline for vehicle + configuration;
- inspect baseline provenance;
- retrieve metric/bin envelope.

Do not allow users to request an unbounded baseline across incompatible configurations.

---

## 57. API — cross-session and modification comparison

Provide typed endpoints/functionality for:

- compare sessions;
- compare configurations;
- compare before/after modification/configuration boundary;
- retrieve trend series.

Bound all inputs.

---

## 58. API status and limitations

Results should include:

- status;
- warnings;
- insufficient-data reasons;
- supported metrics;
- unavailable metrics;
- quality limitations.

Do not turn missing metrics into zero.

---

## 59. Frontend — Analytics Workspace

Add a dedicated Analytics area.

Suggested navigation:

- Overview;
- Sessions;
- Pulls;
- Events;
- Analytics;
- History.

Do not disrupt existing Phase 1–4 inspection flows.

---

## 60. Frontend — Pull Comparison

Allow selecting 2–3 or a bounded number of pulls.

Show:

- comparability;
- common RPM range;
- boost vs RPM;
- IAT vs RPM;
- fuel pressure vs RPM;
- acceleration vs RPM/time where supported;
- metric delta table;
- Phase 3 event markers;
- data-quality warnings.

No “winner” language.

---

## 61. Frontend — repeated-pull view

Provide a sequence view:

```
Pull 1 | Pull 2 | Pull 3 | Pull 4
```

Show factual values such as:

- start IAT;
- end IAT;
- median boost in common range;
- HPFP minimum;
- normalized acceleration metric;
- event count.

Add charts for progression.

---

## 62. Frontend — RPM-normalized curves

Use clear line charts with:

- common axis;
- units;
- legend;
- tooltip;
- coverage indication where useful;
- insufficient-data gaps rather than fabricated interpolation.

Support accessibility.

Do not rely on color alone.

---

## 63. Frontend — Historical Baseline

For selected vehicle/configuration show:

- number of sessions;
- number of pulls;
- date range;
- baseline sufficiency;
- RPM-bin median/envelope;
- current session relative to envelope.

Do not display baseline as manufacturer specification.

Label it explicitly as observed vehicle/configuration history.

---

## 64. Frontend — Modification Comparison

Support selecting a configuration/modification boundary.

Show:

- before sample size;
- after sample size;
- comparability;
- metric deltas;
- quality;
- limitations.

Use factual language:

“Observed before/after difference”.

Do not write:

“Modification caused improvement.”

---

## 65. Frontend — trends

Show longitudinal charts only when sufficient comparable data exists.

Potential:

- acceleration interval over time;
- IAT accumulation over time;
- boost median per RPM band;
- HPFP minimum;
- event frequency.

Clearly show configuration changes on the timeline where possible.

---

## 66. Frontend — insufficient data UX

Good empty states are mandatory.

Examples:

“Only one comparable pull is available. At least N are required for repeatability analysis.”

“No overlapping RPM range is large enough for this comparison.”

“Historical baseline unavailable because this vehicle configuration has insufficient comparable history.”

Never show misleading empty charts.

---

## 67. Acceleration units and display

Canonical storage continues to use canonical units.

UI may display user-friendly units such as km/h, bar, C, MPa.

Conversions must remain deterministic and tested.

Do not change stored canonical semantics.

---

## 68. Analytics provenance UI

Allow advanced inspection of:

- algorithm/version;
- config hash;
- pull/session IDs;
- baseline contributors;
- calculation timestamp;
- quality flags.

This is important for portfolio-grade auditability.

---

## 69. Phase 3 integration

Reference existing events rather than re-detecting them inside Phase 5.

Example:

Repeated-pull analytics may show:

- Pull 3 includes boost_drop;
- Pull 4 includes iat_rise.

Phase 5 may aggregate event counts/patterns, but does not replace the Phase 3 detector engine.

---

## 70. Phase 4 integration

Use acquisition quality and dataset capability assessment.

If Phase 4 says a dataset cannot support boost analytics, Phase 5 must not silently compute a weak boost metric anyway.

Recipes/capabilities inform analytical availability.

---

## 71. Event-rate analytics

Allow factual aggregation such as:

- boost_drop events per comparable pull;
- thermal events per session;
- telemetry-quality events.

Do not transform event frequency into component diagnosis.

---

## 72. Quality weighting/filtering

Define whether poor-quality pulls are:

- excluded;
- included with low-evidence warning;
- usable for only some metrics.

Document and test.

Never silently mix poor and high-quality pulls into one baseline.

---

## 73. Historical data selection

Default baselines should use same:

- vehicle;
- configuration;
- compatible analytics version;
- compatible signal semantics.

Support time bounds where useful.

Do not mix pre/post configuration state by accident.

---

## 74. Configuration timeline correctness

A session must resolve to the configuration active at the session timestamp or explicitly associated configuration.

Test boundary cases around modification timestamps.

Do not retroactively assign a later configuration to earlier sessions.

---

## 75. Modification metadata uncertainty

If exact installation timestamp is unknown, allow an uncertainty/documentation state if repository model supports it.

Do not infer exact before/after boundary from guesswork.

If the current model cannot represent this, document limitation rather than overengineering.

---

## 76. Baseline refresh/rebuild

Provide a deterministic way to rebuild a baseline after new eligible data arrives.

Do not mutate a completed historical run silently.

Record version/timestamp.

---

## 77. Trend segmentation by configuration

Longitudinal graphs should annotate or split when VehicleConfiguration changes.

A single trend spanning incompatible configurations must not be presented as one homogeneous series without explicit segmentation.

---

## 78. Robust statistics library

Centralize tested helpers for:

- median;
- MAD;
- percentile;
- IQR;
- relative delta;
- coefficient of variation when valid;
- Spearman correlation if used;
- robust slope if used.

Avoid scattered bespoke formulas.

---

## 79. Floating point and deterministic results

Ensure deterministic ordering and numeric calculation where possible.

Document tolerances.

Tests should not fail due to unstable ordering or insignificant floating-point noise.

---

## 80. Idempotency

Repeated identical analytics requests should not create duplicate persisted results.

Use stable identities based on:

- analytics type;
- algorithm version;
- config hash;
- source set/fingerprint;
- vehicle/configuration.

Explicit recompute semantics should remain auditable.

---

## 81. Migration safety

Do not edit any applied Phase 0–4 migration.

Discover the current Alembic head programmatically.

Create new Phase 5 revision(s).

Continue using the structural migration-head guard introduced in Phase 4.

Do not hardcode stale previous-head assertions throughout tests.

---

## 82. Migration acceptance

In disposable TimescaleDB validate:

1. clean upgrade to current head;
2. Phase 5 tables/structures exist;
3. downgrade Phase 5 revision to its parent;
4. Phase 0–4 schema remains;
5. Phase 5-specific structures disappear as intended;
6. re-upgrade to head;
7. repeated upgrade is safe;
8. full downgrade according to project policy;
9. final clean upgrade;
10. Timescale extension remains;
11. telemetry hypertable remains;
12. acquisition/Phase 4 schema remains correct.

---

## 83. Unit tests

Cover at minimum:

- comparability dimensions;
- common window selection;
- RPM binning;
- bin minimum coverage;
- robust statistics;
- pull metrics;
- boost analytics;
- thermal analytics;
- fuel analytics;
- acceleration interval interpolation;
- interval quality rejection;
- repeatability;
- repeated-pull sequence;
- cross-session comparison;
- baseline sufficiency;
- baseline envelope;
- trend sufficiency;
- configuration separation;
- before/after comparison;
- correlation minimum sample guard;
- idempotency;
- config hashing;
- insufficient-data states;
- quality integration.

---

## 84. Integration tests

Against disposable real TimescaleDB test:

- migration;
- ingest synthetic multi-session history;
- Phase 2 pulls;
- Phase 3 events;
- Phase 4 capability/quality metadata;
- Phase 5 pull analytics;
- repeated-pull analytics;
- cross-session comparison;
- baseline creation;
- baseline rebuild/new version;
- configuration isolation;
- before/after analysis;
- trend query;
- result filtering;
- idempotency.

---

## 85. Real-stack E2E

Create an end-to-end scenario using the real API and frontend.

At minimum:

1. create/use synthetic BMW 335i F30/N55;
2. create configuration A;
3. create several sessions with comparable pulls;
4. generate a repeated-pull thermal/boost pattern;
5. run canonical Phase 2;
6. run canonical Phase 3;
7. run Phase 5 analytics;
8. open Analytics workspace;
9. compare pulls;
10. view RPM-normalized chart;
11. view repeated-pull progression;
12. view session summary;
13. build/view vehicle baseline;
14. create configuration/modification B;
15. create post-change sessions;
16. run before/after comparison;
17. verify configuration separation;
18. verify insufficient-data behavior for an intentionally unsupported comparison;
19. capture screenshot artifacts.

Do not mock the core backend analytics path.

---

## 86. Phase 5 acceptance dataset

Create a deterministic acceptance dataset containing multiple sessions and two configurations.

Suggested structure:

Configuration A:

- 3+ sessions;
- multiple comparable pulls;
- stable baseline plus one progressive thermal sequence.

Configuration B:

- 2+ sessions;
- deliberate controlled factual differences.

Include poor-quality/non-comparable sessions that must be excluded or flagged.

---

## 87. Acceptance metrics

Do not use precision/recall as the primary metric for deterministic continuous analytics.

Instead report:

- expected numeric value/band;
- actual;
- absolute error;
- relative error where meaningful;
- expected comparison accepted/rejected;
- expected sufficiency state;
- expected trend direction;
- expected configuration membership.

All golden scenarios must pass tolerances.

---

## 88. Benchmark

Benchmark Phase 5 using at least 100k telemetry observations and enough sessions/pulls to exercise history.

Report:

- input observations;
- sessions;
- pulls;
- bin count;
- normalization duration;
- per-pull analytics duration;
- repeated-pull duration;
- baseline construction;
- cross-session comparison;
- trend generation;
- total;
- peak Python memory if practical.

Do not create hard exact-latency SLOs yet.

---

## 89. Observability

Add bounded-cardinality metrics for:

- analytics runs;
- analytics duration by type;
- pull comparisons;
- rejected comparisons by bounded reason;
- insufficient-data outcomes;
- baseline builds;
- baseline contributor counts in histogram form;
- trend builds;
- analytics failures.

No vehicle/session/pull IDs as metric labels.

---

## 90. Tracing

Add spans around:

- source selection;
- telemetry load;
- comparability calculation;
- normalization;
- metric extraction;
- baseline load/build;
- aggregation;
- persistence.

Do not put giant arrays or raw telemetry in traces.

---

## 91. Logging

Structured logs may include:

- analytics type;
- algorithm version;
- bounded counts;
- rejected reason category;
- elapsed time;
- warning category.

Do not log raw telemetry payloads, VINs, or large evidence arrays.

---

## 92. Security and abuse limits

Threat-model:

- huge comparison request;
- thousands of sessions;
- expensive history scans;
- pathological RPM-bin size;
- invalid percentile config;
- repeated baseline rebuild abuse;
- oversized result payload;
- SQL/filter abuse.

Use typed validation and resource limits.

Do not allow arbitrary executable formulas from clients.

---

## 93. No arbitrary analytics expressions

Do not implement user-supplied Python/SQL/expression execution.

Analytics configuration must be from allowlisted typed fields.

---

## 94. Phase 5 dependencies

If adding Polars, DuckDB, SciPy, NumPy, or another analytical dependency:

- justify it;
- pin/lock it;
- security scan it;
- benchmark it;
- avoid dependency duplication.

Prefer current dependencies if sufficient.

---

## 95. No ML yet

Do not add:

- learned baseline;
- anomaly ML;
- predictive maintenance;
- forecasting model;
- clustering;
- neural nets;
- Isolation Forest;
- MLflow;
- feature store.

Phase 9 handles ML.

Deterministic statistics and trend estimation are allowed.

---

## 96. No agents/MCP/RAG yet

Do not add:

- MCP;
- LangGraph;
- LLM calls;
- agent reasoning;
- natural-language analytics;
- RAG/vector DB.

Phase 6 will expose Phase 5 analytics as tools.
Phase 7 will orchestrate them.
Phase 8 will add technical knowledge retrieval.

---

## 97. Future MCP readiness

Design Phase 5 services so future tools can expose clean operations such as:

- get_pull_analytics;
- compare_pulls;
- get_repeated_pull_analysis;
- get_session_analytics;
- get_vehicle_baseline;
- compare_sessions;
- compare_configurations;
- get_modification_comparison;
- get_vehicle_trends.

Do not build the MCP server yet.

---

## 98. Future agent readiness

Results must be structured enough that a future agent can reason from facts.

Example future tool response should make it possible to determine:

- IAT increased;
- boost decreased;
- HPFP remained stable;
- acceleration became slower;
- how comparable the pulls were;
- how many samples support the statement;
- whether history is sufficient.

No natural-language reasoning layer required now.

---

## 99. Documentation

Add detailed docs covering:

- analytics architecture;
- comparability;
- RPM normalization;
- pull analytics;
- repeated-pull analytics;
- acceleration intervals;
- robust statistics;
- correlation guardrails;
- session analytics;
- historical baseline;
- trend analytics;
- modification/configuration comparison;
- data sufficiency;
- provenance;
- limitations;
- source-of-truth hierarchy.

Explicitly state:

“Observed association is not root-cause diagnosis.”

---

## 100. ADR

Create one or more strong ADRs documenting:

- analytics result/persistence strategy;
- comparability and normalization;
- historical baseline versioning/reproducibility;
- decision to remain deterministic and defer ML/causal diagnosis.

Avoid unnecessary ADR fragmentation.

---

## 101. AGENTS.md / repository workflow

Update AGENTS.md with Phase 5 context.

Consider adding a local analytics-change workflow/skill requiring:

- metric definition;
- unit;
- comparability assumptions;
- synthetic numeric fixture;
- insufficient-data test;
- configuration/version review;
- benchmark impact;
- documentation.

Only add it if consistent with existing repo local skills.

---

## 102. Make targets

Add:

make phase5-acceptance

Optionally:

make analytics-benchmark

Preserve:

- phase3-acceptance;
- phase4-acceptance;
- stream tests;
- all prior quality/security gates.

verify-cloud should continue to run prior phase regression acceptance plus Phase 5 non-container acceptance.

Canonical verify/full-validation must include required Phase 5 integration/E2E/benchmark coverage.

---

## 103. CI regression protection

Phase 5 must not disable:

- Phase 3 event golden tests;
- Phase 4 acquisition tests;
- streaming benchmark/gates;
- migration guard;
- security scans;
- observability;
- contracts;
- browser E2E.

New Phase 5 green status is meaningful only if prior phases remain green.

---

## 104. Push early

After the first coherent vertical slice:

- commit;
- push to codex/phase-5-automotive-analytics;
- verify remote SHA;
- confirm workflows start.

Do not wait until the end to discover GitHub failures.

Use the same branch for all fixes.

Do not create phase-5-fix/final/v2 branches.

---

## 105. Pull request

Create exactly one pull request:

Base: main
Head: codex/phase-5-automotive-analytics

Suggested title:

feat: add Phase 5 automotive analytics

Do not merge automatically.

---

## 106. GitHub workflow behavior

Monitor actual commit-tied:

- CI;
- Security;
- canonical full validation.

If anything fails:

- inspect exact job/log;
- fix root cause;
- push same branch;
- repeat.

Do not return a final delivery report while mandatory workflows are queued, running, red, or cancelled.

This requirement is strict.

---

## 107. Do not repeat the premature Phase 4 completion behavior

The task is not finished when:

- implementation compiles;
- local non-Docker tests pass;
- PR is created;
- workflows have merely started.

The task is finished only when the complete Phase 5 specification is implemented and the latest remote head has final green canonical evidence.

If a workflow is still running, continue monitoring it.

If it fails, fix it before returning.

---

## 108. Definition of Done — analytics core

Complete only when:

- comparability is formalized;
- common windows work;
- RPM normalization works;
- pull analytics works;
- repeated-pull analysis works;
- session analytics works;
- cross-session comparison works;
- historical vehicle/configuration baseline works;
- modification/configuration comparison works;
- trend analytics works;
- quality/sufficiency guardrails work.

---

## 109. Definition of Done — evidence

Complete only when every analytical conclusion has:

- source/provenance;
- unit;
- metric definition;
- quality state;
- comparability evidence;
- algorithm/version;
- config hash;
- sufficient-data state.

---

## 110. Definition of Done — UI

Complete only when a user can:

- open Analytics;
- compare pulls;
- inspect common RPM window;
- inspect normalized curves;
- inspect repeated-pull progression;
- inspect session summary;
- inspect historical baseline;
- inspect trends;
- inspect configuration/modification before/after;
- understand insufficient-data states.

---

## 111. Definition of Done — tests

Complete only when:

- unit tests pass;
- golden numeric Phase 5 scenarios pass;
- integration tests pass;
- real-stack E2E passes;
- migration chain passes;
- benchmark executes;
- Phase 3 regression passes;
- Phase 4 regression passes;
- security passes;
- observability passes;
- contracts pass.

---

## 112. Definition of Done — GitHub

The latest remote head must have:

CI: SUCCESS
Security: SUCCESS
Canonical full validation: SUCCESS

Do not claim Phase 5 complete otherwise.

---

## 113. Final delivery report

Return:

PHASE 5 DELIVERY REPORT

Include:

### Status

Only state:
PHASE 5: COMPLETE
PHASE 6: READY

when all software acceptance criteria and commit-tied canonical GitHub workflows are green.

### Repository

- branch;
- baseline;
- commits;
- PR;
- remote head;
- working tree.

### Architecture

- analytics pipeline;
- normalization;
- comparability;
- result persistence;
- versioning/idempotency.

### Metrics implemented

- pull metrics;
- boost;
- thermal;
- fuel;
- acceleration/performance intervals;
- repeatability;
- correlation/association where applicable.

### Higher-level analytics

- repeated pulls;
- session analytics;
- cross-session;
- baseline;
- trends;
- modification/configuration comparison.

### Synthetic/golden validation

Report scenarios and numeric tolerances/results.

### Data sufficiency / false conclusions

Report rejected comparisons, poor-quality cases, and insufficient-history behavior.

### Benchmark

Report observations, sessions, pulls, timings, memory where measured.

### API

List endpoints.

### Frontend

Describe Analytics workspace and screenshots.

### Migrations

- previous discovered head;
- new head;
- downgrade/re-upgrade;
- structural migration guard.

### Testing

- unit;
- integration;
- E2E;
- contracts;
- phase3 acceptance;
- phase4 acceptance;
- phase5 acceptance.

### Observability

- metrics;
- traces;
- bounded cardinality.

### Security

- resource limits;
- validation;
- scans.

### GitHub

- CI run ID/result;
- Security run ID/result;
- canonical full-validation run ID/result.

### Explicit deferrals

- root-cause diagnosis;
- repair recommendations;
- Phase 6 MCP;
- Phase 7 agents;
- Phase 8 RAG;
- ML/predictive maintenance;
- causal inference;
- unsupported BMW proprietary signals.

Do not return the final report until the latest remote head has final green evidence.
