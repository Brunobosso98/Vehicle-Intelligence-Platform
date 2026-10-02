# Phase 4 — Streaming & Live Vehicle Acquisition

Implement Phase 4 — Streaming & Live Vehicle Acquisition for the Vehicle Intelligence Platform / N55 Intelligence Lab.

## Repository and branch

Repository: Brunobosso98/Vehicle-Intelligence-Platform

Work only on the existing branch:

codex/phase-4-streaming-live-acquisition

This branch was created directly from the Phase 3 merged main baseline:

b6c415a66cf282d80866901a77e48c0a6c266bf8

Do not work directly on main.
Do not create another Phase 4 branch.
Do not implement Phase 5, Phase 6, Phase 7, RAG, agents, or ML.

Treat this as a production-grade engineering platform milestone, not a prototype.

---

## 1. Product definition

Phase 4 transforms the platform from an offline telemetry-analysis system into a system capable of guiding data acquisition and ingesting vehicle telemetry continuously.

Target flow:

~~~
Known analysis objective
        ↓
Structured Logging Recipe
        ↓
Required / recommended signals
        ↓
Vehicle / adapter capability discovery
        ↓
Sampling plan
        ↓
Acquisition
   ↙           ↘
File/replay    Live OBD
        ↓
Quality monitoring
        ↓
Streaming ingestion
        ↓
Canonical telemetry
        ↓
Phase 2 temporal understanding
        ↓
Phase 3 factual event detection
        ↓
Live provisional feedback
        ↓
Canonical final analysis
~~~

Critical boundary:

Phase 4 knows how to fulfill predefined acquisition objectives.

Phase 7 will later understand arbitrary natural-language intent and decide which Phase 4 recipe/tool to use.

Do not implement free-text intent understanding, an agent, LangGraph, MCP, RAG, or LLM-driven recipe selection in this phase.

---

## 2. Verify git, remote, baseline, and auth before substantial work

Run:

~~~
git status
git branch --show-current
git log --oneline -10
git remote -v
git merge-base HEAD b6c415a66cf282d80866901a77e48c0a6c266bf8
~~~

Current branch must be:

codex/phase-4-streaming-live-acquisition

It must descend from:

b6c415a66cf282d80866901a77e48c0a6c266bf8

If origin is missing:

~~~
git remote add origin https://github.com/Brunobosso98/Vehicle-Intelligence-Platform.git
~~~

If origin exists with the wrong URL:

~~~
git remote set-url origin https://github.com/Brunobosso98/Vehicle-Intelligence-Platform.git
~~~

Then verify:

~~~
git remote -v
git ls-remote origin refs/heads/codex/phase-4-streaming-live-acquisition
git push --dry-run origin HEAD:codex/phase-4-streaming-live-acquisition
~~~

If authentication cannot publish, fix it before substantial implementation.

Do not repeat the old unpublished-workspace failure mode.

---

## 3. Read current repository context

Before implementation, read and understand:

- root AGENTS.md;
- nested AGENTS.md files;
- README;
- roadmap;
- architecture docs;
- testing strategy;
- security docs;
- observability docs;
- ADRs;
- Phase 1 canonical telemetry;
- Phase 1 TelemetrySource and LiveOBDSource boundaries;
- Phase 2 alignment, segmentation and pull detection;
- Phase 2 synthetic scenarios;
- Phase 3 event/anomaly engine;
- Phase 3 baseline and evidence contracts;
- current SQLAlchemy models;
- Alembic revisions;
- API routes;
- generated OpenAPI and TypeScript contracts;
- Next.js UI;
- Docker Compose;
- Makefile;
- integration scripts;
- GitHub CI;
- Security workflow;
- canonical full-validation workflow;
- validation summary tooling.

Preserve completed Phase 0–3 behavior.

Do not rebuild existing systems from scratch when reusable boundaries already exist.

---

## 4. Update phase context

After implementation, documentation must state accurately:

- Phase 0 complete;
- Phase 1 complete;
- Phase 2 complete;
- Phase 3 complete;
- Phase 4 current or complete depending validation;
- Phase 5+ planned.

Rename roadmap wording from only “Streaming Architecture” to “Streaming & Live Vehicle Acquisition” where appropriate.

Preserve historical evidence.

---

## 5. Safety boundary

Phase 4 is read-only vehicle acquisition.

Allowed:

- read telemetry;
- query supported standard OBD capabilities/PIDs;
- configure logging rates;
- start/stop software recording;
- stream data;
- analyze data;
- detect factual events;
- display provisional alerts.

Forbidden:

- ECU coding;
- ECU flash;
- tune/map writes;
- adaptation writes;
- throttle actuation;
- brake actuation;
- steering;
- transmission control;
- actuator tests;
- automatic clearing of safety-critical state;
- closed-loop vehicle control.

Hardware adapters must expose read-only capabilities only.

Do not implement arbitrary ECU command execution.

---

## 6. Operational safety

Do not encourage performance testing on public roads.

UI/docs involving pulls must state that controlled acceleration testing belongs only in lawful appropriate environments such as a closed course or dyno.

The platform observes; it does not command the driver or vehicle.

---

## 7. Target architecture

Introduce explicit boundaries for:

~~~
Vehicle / OBD adapter
        ↓
Local Acquisition Collector
        ↓
Acquisition Gateway
        ↓
Durable Stream
        ↓
Streaming Consumer / Normalizer
        ↓
TimescaleDB
        ↓
Live Analysis Coordinator
        ↓
WebSocket or SSE
        ↓
Next.js live dashboard
~~~

Preserve a modular architecture.

The FastAPI application may remain the primary API deployable.

A separate collector process/package is justified because it runs near physical hardware.

A streaming worker is justified if required by the durable-stream design.

Do not create gratuitous microservices.

---

## 8. Streaming technology decision

Phase 4 is the first phase where a durable Kafka-compatible stream is justified.

Evaluate and document the decision in an ADR.

Prefer Redpanda if it gives:

- Kafka protocol compatibility;
- straightforward Docker operation;
- simple local development;
- reasonable CI resource requirements;
- lower operational complexity.

Kafka itself is acceptable if repository constraints provide a concrete reason.

Do not add both.

Document:

- why durable streaming is needed now;
- why direct database writes alone are not enough for live acquisition;
- at-least-once delivery semantics;
- replay;
- consumer offset behavior;
- recovery;
- retention;
- operational tradeoffs.

---

## 9. Stream contracts

Define versioned stream contracts.

Potential topics:

- telemetry.raw.v1
- telemetry.canonical.v1
- acquisition.status.v1
- analysis.live-events.v1

Use fewer topics if a simpler topology is sufficient.

Every message must carry the concepts needed for reproducibility:

- schema version;
- stable event/message ID;
- acquisition session ID;
- source ID;
- safe vehicle reference;
- observed time;
- produced time;
- sequence number when applicable;
- provenance;
- payload.

No secrets in stream messages.

---

## 10. Delivery semantics and idempotency

Design explicitly for at-least-once delivery.

Do not claim exactly-once unless proven end to end.

Expected behavior:

~~~
collector may resend
stream may redeliver
consumer may retry
database remains idempotent
~~~

Reuse Phase 1 canonical telemetry identity/idempotency.

The final Timescale representation must not duplicate an observation because of retry, reconnect, consumer restart, or replay.

---

## 11. Ordering and time semantics

Do not assume arrival order.

Support:

- delayed frames;
- out-of-order frames;
- duplicate frames;
- reconnect replay.

Preserve:

- observed_at;
- ingested_at;
- source sequence;
- source provenance.

Phase 2 and Phase 3 canonical final analysis remains event-time based.

Use UTC.

Where collector clock skew is possible, preserve collector observed time and server receive time and expose suspicious skew instead of silently rewriting event time.

---

## 12. Local acquisition collector

Create a dedicated Python collector application/package.

Responsibilities:

- adapter connection;
- capability discovery;
- recipe loading;
- sampling plan execution;
- signal polling;
- event timestamping;
- sequence assignment;
- quality metadata;
- local buffering;
- streaming/upload;
- reconnect;
- heartbeat;
- status reporting;
- graceful shutdown.

No frontend logic belongs in the collector.

---

## 13. Collector CLI

Provide a usable CLI along these lines:

~~~
vehicle-collector devices
vehicle-collector probe
vehicle-collector recipes
vehicle-collector preflight --recipe performance-pull
vehicle-collector start --recipe performance-pull
vehicle-collector replay session.csv
~~~

Exact names may differ.

Requirements:

- good human-readable errors;
- optional JSON output where useful;
- Ctrl+C handling;
- connection timeout;
- bounded retry;
- deterministic exit codes;
- no secret token leakage.

---

## 14. Vehicle adapter protocol

Create a generic read-only adapter protocol.

Conceptually:

~~~
class VehicleDataAdapter(Protocol):
    async def connect(self) -> None: ...
    async def capabilities(self) -> DeviceCapabilities: ...
    async def read(self, plan: SamplingPlan) -> AsyncIterator[RawTelemetryRecord]: ...
    async def close(self) -> None: ...
~~~

Exact interface may differ.

Do not expose arbitrary ECU write/command methods.

---

## 15. Required acquisition adapters

Implement at minimum:

### Synthetic live adapter

Deterministic and CI-friendly.

Support:

- normal operation;
- cruise;
- pull scenarios;
- Phase 3 anomaly scenarios;
- jitter;
- dropout;
- reconnect;
- out-of-order frames;
- accelerated real-time mode for tests.

### Replay adapter

Replay persisted/canonical or supported imported telemetry as if live.

Support:

- real-time speed;
- accelerated speed;
- deterministic test timing.

### Real read-only OBD adapter path

Implement a concrete read-only ELM327-compatible path if technically viable.

Support standardized OBD-II signals where exposed.

Do not claim physical compatibility with the user’s Vgate vLinker until real hardware validation is performed.

Do not fabricate BMW manufacturer-specific PID mappings.

If hardware cannot be exercised in CI/Codex:

- unit-test transport/protocol behavior using deterministic fake transport;
- document physical verification as pending;
- do not pretend hardware was tested.

---

## 16. BMW / Vgate extension boundary

Create a clean future adapter boundary for BMW F-series / Vgate vLinker enhanced telemetry.

Do not guess proprietary commands.

Generic OBD-II discovery may be implemented now.

BMW enhanced telemetry requires evidence from actual hardware/logs or authoritative documentation.

---

## 17. Standard PID capability discovery

Where adapter/protocol supports standard OBD capability discovery:

- query supported standard PID ranges;
- map known standard signals to canonical signal definitions;
- report unsupported/unknown values explicitly.

Represent states such as:

- supported;
- unsupported;
- unavailable;
- unknown;
- adapter does not support discovery.

---

## 18. LoggingRecipe as a first-class domain concept

Create a first-class structured LoggingRecipe model.

Concepts should include:

- id/key;
- name;
- description;
- known objective;
- version;
- deterministic configuration hash;
- vehicle scope;
- required signals;
- recommended signals;
- optional signals;
- sampling priorities;
- minimum usable rate;
- preferred rate;
- minimum duration;
- quality requirements;
- required context;
- supported acquisition modes;
- notes.

Recipes must be versioned.

Do not silently mutate historical recipe meaning.

---

## 19. Known objective to structured recipe

Implement deterministic mapping:

~~~
known objective
    ↓
structured recipe
    ↓
signal requirements
~~~

Initial objective keys should include at least:

- general_health;
- performance_pull;
- thermal_behavior;
- fuel_delivery;
- boost_behavior;
- data_quality_validation.

Do not interpret arbitrary free-text user questions.

That is Phase 7.

---

## 20. Phase 7 boundary

Phase 4 may expose deterministic APIs such as:

- GET /api/v1/logging/objectives
- GET /api/v1/logging/recipes
- GET /api/v1/logging/recipes/{id}
- POST /api/v1/logging/recipes/{id}/preflight

Phase 7 will later consume them.

Do not add an LLM intent classifier.

Do not add LangGraph.

Do not add agent orchestration.

---

## 21. Initial Performance Pull recipe

Create a structured recipe for performance-pull acquisition.

Example semantics:

Required:
- engine RPM;
- vehicle speed;
- throttle position.

Strongly recommended:
- boost / manifold pressure;
- intake air temperature.

Recommended where available:
- high-pressure fuel pressure;
- lambda/equivalence ratio;
- ignition-related channels.

Context:
- oil temperature;
- coolant temperature.

Do not make currently unavailable/proprietary signals hard requirements.

The recipe must degrade gracefully.

---

## 22. Initial Thermal Behavior recipe

Goal: support factual thermal comparison across repeated comparable operating windows.

Useful signals:

- RPM;
- throttle;
- vehicle speed;
- boost/load;
- intake air temperature;
- oil temperature;
- coolant temperature;
- ambient temperature if available.

Do not label the conclusion as heat soak.

Phase 3 factual semantics remain authoritative.

---

## 23. Initial Fuel Delivery recipe

Collect evidence useful for factual fuel-pressure behavior.

Potential signals:

- RPM;
- throttle/load;
- high-pressure fuel pressure;
- low-pressure fuel pressure if available;
- boost/load;
- lambda if available.

If requested-vs-actual rail pressure is unavailable, do not pretend it can analyze requested tracking.

---

## 24. Initial General Health recipe

Provide broad low-risk observational coverage.

Do not simply request every PID.

Balance channel count and temporal resolution.

---

## 25. Recipe signal requirement structure

A signal requirement should include more than a signal key.

Potential fields:

- canonical signal;
- requirement importance;
- reason;
- minimum Hz;
- preferred Hz;
- whether capability survives without it;
- degraded capabilities if absent.

Example concept:

~~~
signal: engine.boost_pressure
importance: recommended
preferred_hz: 10
reason: supports boost behavior and pull comparison
missing_effect:
  - boost anomaly detection unavailable
~~~

---

## 26. Recipe and PID mapping are separate

A recipe says what information is needed.

An adapter says how or whether it can obtain it.

Do not encode unverified BMW-specific PID numbers in recipes.

---

## 27. Canonical signal extension

Phase 4 may add generic canonical signals required by recipes, such as:

- ambient air temperature;
- lambda/equivalence ratio;
- low fuel pressure;
- accelerator pedal position;
- ignition timing;
- timing correction;
- misfire count.

But only when semantics, canonical unit, range, and source mapping are responsibly defined.

Do not activate Phase 3 detectors for signals that have not been responsibly sourced/tested.

---

## 28. Recipe preflight

Implement structured preflight evaluation.

Inputs:

- recipe;
- device/adapter capabilities;
- vehicle/configuration.

Outputs:

- required signals available;
- required signals missing;
- recommended signals available;
- optional signals available;
- sampling plan;
- estimated rates;
- expected analysis capabilities;
- unavailable capabilities;
- warnings;
- readiness.

Readiness states should be explicit, such as:

- ready;
- degraded;
- blocked.

Example:

Performance Pull with RPM/speed/throttle/boost/IAT available but timing correction absent should be usable with limitations.

Performance Pull without RPM should be blocked.

Readiness is acquisition suitability, never a vehicle-health score.

---

## 29. Post-log capability assessment

After file upload or completed live acquisition, evaluate the actual dataset.

Report:

- available signals;
- effective sample rate per signal;
- gaps;
- missing regions;
- duration;
- completeness;
- recipe adherence;
- usable analyses;
- unavailable analyses and why.

The platform must be able to say:

“This dataset supports pull detection, boost analysis and thermal analysis, but not ignition-correction analysis because the required channel is absent.”

Do not conflate lack of capability with lack of anomaly.

---

## 30. Reusable Dataset Capability Engine

Make capability assessment a typed reusable backend service/domain contract.

A future agent should be able to ask:

“Can dataset X support capability Y?”

and receive structured evidence.

Do not implement this only as frontend strings.

---

## 31. Sampling planner

Implement deterministic sampling planning.

Inputs:

- recipe;
- device capabilities;
- adapter throughput constraints;
- desired rates.

Outputs:

- selected signals;
- priority;
- target polling frequency;
- estimated effective frequency;
- optional signals dropped/reduced;
- warnings.

Protect critical signals from optional-channel starvation.

---

## 32. Sampling priority

Use a clearly documented vocabulary such as:

- critical_for_recipe;
- high;
- normal;
- low.

Do not confuse sampling priority with safety severity.

---

## 33. OBD polling budget

Do not assume every PID can be sampled at 20 Hz simultaneously.

Scheduler must account for:

- per-signal rate;
- request/response latency;
- adapter throughput;
- priority;
- timeout;
- failed reads.

Lower-priority signals should degrade first when the adapter cannot meet all target rates.

---

## 34. Effective sample-rate measurement

Measure and expose actual effective sampling rate.

For each signal track:

- target Hz;
- actual Hz;
- jitter;
- stale ratio;
- missing ratio.

Do not report requested rate as if it were achieved rate.

---

## 35. Live data-quality monitor

During collection, expose structured quality indicators:

- adapter connection state;
- adapter latency;
- overall throughput;
- per-signal effective rate;
- signal staleness;
- missing observations;
- queue lag;
- local spool occupancy;
- broker/consumer lag;
- duplicate count;
- reconnect count;
- dropped-sample count.

Avoid one opaque quality score as the only representation.

---

## 36. Live dashboard

Create a real-time UI.

At minimum show:

- acquisition status;
- selected recipe;
- selected vehicle;
- elapsed time;
- device state;
- stream state;
- RPM;
- speed;
- throttle;
- boost when available;
- IAT when available;
- fuel pressure when available;
- oil/coolant temperature when available;
- actual signal rates;
- data-quality warnings.

Use WebSocket or SSE based on a documented decision.

Do not poll the database at an extremely high frequency from the browser.

---

## 37. Live charts

Use a bounded rolling window.

For example:

- last 30 seconds;
- last 60 seconds;
- configurable bounded maximum.

Do not continually send full session history to the browser.

Historical data remains server-side.

---

## 38. Live Phase 2 behavior

Integrate existing Phase 2 temporal understanding into the live path.

Reuse/refactor shared deterministic logic where possible.

Support provisional detection of at least:

- idle;
- acceleration;
- pull;
- deceleration.

Do not create an unrelated second implementation of pull detection.

---

## 39. Provisional versus canonical final analysis

This distinction is mandatory.

Live data is incomplete and may be delayed/out of order.

Therefore live analysis must be explicitly marked provisional.

At session completion:

1. drain/persist telemetry;
2. run canonical Phase 2 over settled event-time data;
3. run canonical Phase 3;
4. produce final persisted pulls/events;
5. reconcile provisional live findings against final results.

Never make provisional results indistinguishable from canonical results.

---

## 40. Live pull UX

During a possible pull, UI may show:

“Possible pull in progress”.

After live closure:

“Provisional pull detected”.

After final canonical analysis:

“Finalized Pull #N”.

Open temporal events do not yet have authoritative final boundaries.

---

## 41. Live Phase 3 factual events

Allow a streaming or bounded micro-batch version of factual Phase 3 detection where technically justified.

Examples:

- telemetry gap;
- sensor dropout;
- high temperature;
- sustained boost behavior;
- fuel-pressure behavior.

Live events must be labeled provisional.

Do not emit physical root-cause claims.

Example allowed:

“Possible fuel-pressure event detected — provisional.”

Not allowed:

“HPFP failure.”

---

## 42. Provisional event reconciliation

After session finalization, a provisional event may be:

- confirmed;
- boundary-adjusted;
- merged;
- changed;
- absent in final analysis.

Design this reconciliation explicitly.

If provisional events are persisted, preserve provenance and reconciliation status.

---

## 43. Bounded live-analysis windows

Do not rerun full-session analysis every few hundred milliseconds.

Use incremental state or bounded rolling micro-batches.

Document window size and tradeoffs.

---

## 44. Acquisition session lifecycle

If current DrivingSession is insufficient for operational state, introduce a distinct acquisition-session model.

Potential states:

- created;
- preflight;
- connecting;
- recording;
- reconnecting;
- stopping;
- finalizing;
- completed;
- failed;
- aborted.

Operational acquisition lifecycle and analytical DrivingSession should remain conceptually distinct.

An acquisition session should eventually resolve into or attach to a canonical DrivingSession.

---

## 45. Acquisition start and stop

Starting an acquisition associates:

- vehicle;
- active vehicle configuration;
- recipe;
- source/adapter;
- capability snapshot;
- sampling plan;
- optional safe metadata.

Stopping must:

- define a clear final observation boundary;
- stop accepting normal new frames after closure;
- drain valid buffered messages;
- persist outstanding telemetry;
- settle stream state;
- run canonical Phase 2;
- run canonical Phase 3;
- produce final quality/capability assessment.

Analysis failure must not erase raw canonical telemetry.

---

## 46. Heartbeats and status

Collector should emit bounded status/heartbeat messages.

Detect:

- disconnected collector;
- silent collector;
- stalled adapter.

These are acquisition-state issues, not vehicle anomalies.

---

## 47. Durable local offline spool

Live acquisition must tolerate temporary connectivity loss.

Implement a bounded durable local spool.

SQLite is acceptable if justified.

Requirements:

- durable;
- ordered;
- bounded;
- retryable;
- idempotent;
- crash-safe;
- inspectable;
- no secret leakage.

Do not retain unbounded telemetry forever.

---

## 48. Buffer policy

Define thresholds:

- normal;
- warning;
- near capacity;
- capacity reached.

If capacity is exceeded, use an explicit documented policy.

Prefer retaining already queued durable data and reducing/dropping lowest-priority future samples where reasonable.

Never silently drop samples.

Track dropped counters and reasons.

---

## 49. Reconnect

Use bounded exponential backoff with jitter.

Recover safely from:

- gateway restart;
- temporary internet/Wi-Fi loss;
- broker restart;
- recoverable adapter timeout.

Avoid infinite tight retry loops.

---

## 50. Replay after reconnect

Buffered data retains original:

- observed_at;
- identity;
- sequence;
- source provenance.

After reconnect:

- replay;
- deduplicate downstream;
- retain event-time semantics.

Do not replace event time with reconnect time.

---

## 51. Backpressure

The pipeline must not use unlimited memory.

Use:

- bounded in-memory queues;
- flow control;
- durable local spool;
- retry semantics;
- metrics.

Test backpressure.

---

## 52. Acquisition authentication

Do not leave a live ingestion endpoint open to arbitrary writes.

Use scoped acquisition credentials.

Recommended pattern:

- high-entropy server-generated token;
- short-lived or session-scoped;
- stored hashed if persisted;
- valid only for one acquisition session;
- invalidated on completion.

Never log the raw token.

Do not introduce an unrelated full user identity platform unless needed.

---

## 53. Network and broker security

Document production expectations:

- HTTPS/TLS;
- WSS if WebSocket;
- scoped token;
- broker isolated from public internet.

Local development may use localhost/plain HTTP.

Do not expose Kafka/Redpanda publicly by default.

---

## 54. Gateway validation

Validate before stream publication:

- acquisition token;
- schema version;
- batch size;
- payload size;
- timestamps;
- source;
- sequence;
- canonical signal key where applicable;
- source identity.

Reject malformed data early.

---

## 55. Batched ingestion

Support bounded batches.

Do not require one HTTP request for every telemetry observation.

Benchmark meaningful batch sizes.

---

## 56. Stream schema evolution

Version stream message schemas.

Do not silently alter semantics.

JSON + Pydantic is acceptable initially if justified.

Do not add Avro/Protobuf/schema-registry infrastructure purely for novelty.

---

## 57. Stream consumer responsibilities

Consumer must:

- decode/validate;
- normalize where required;
- preserve provenance;
- persist canonical observations;
- handle redelivery;
- commit offsets according to documented durability semantics;
- emit status/metrics;
- feed bounded live analysis.

---

## 58. Poison message handling

Malformed input must not permanently block consumption.

Implement bounded retries and a practical quarantine/error-record strategy.

Avoid unnecessary enterprise DLQ complexity.

---

## 59. Replayability

The streaming architecture must support deterministic replay for:

- synthetic fixtures;
- persisted sessions;
- recorded stream fixtures;
- canonical telemetry.

This is important for later analytics, ML, and agent evaluation.

---

## 60. BimmerLink / file acquisition

Improve file-based acquisition without fabricating BimmerLink format support.

Do not claim a BimmerLink parser until a real BimmerLink export is available.

Create mapping/import infrastructure capable of:

- column mapping;
- unit identification;
- preview;
- validation;
- unknown/unmapped columns;
- explicit resolution for ambiguous mappings.

When a real BimmerLink file is later provided, add a specific adapter based on that actual schema.

---

## 61. Same recipes for file and live acquisition

Logging Recipes are shared across acquisition modes.

The same recipe should answer both:

“What should I select in BimmerLink?”

and:

“What should the live collector poll?”

This is a core product abstraction.

---

## 62. Post-import recipe validation

After import, report actual recipe coverage.

Example concept:

~~~
Requested recipe: Performance Pull

Required coverage: 3/3
Recommended coverage: 2/4

Result: usable with limitations
~~~

Expose exact limitations.

---

## 63. Device capability model

Persist/cache a structured capability snapshot when useful.

Concepts:

- adapter type;
- discovered signals;
- discovery timestamp;
- transport;
- observed throughput;
- manufacturer-enhanced support status;
- safe firmware metadata if available.

Allow refresh.

Do not assume capabilities never change.

Avoid exposing raw device identifiers, MAC addresses, serials, or VINs unnecessarily.

---

## 64. Synthetic live generator

Mandatory for CI.

Extend current synthetic infrastructure to emit live telemetry.

Support deterministic modes:

- healthy normal drive;
- cruise;
- performance pull;
- boost drop;
- fuel-pressure drop;
- IAT rise;
- sensor dropout;
- telemetry gap;
- connection loss;
- noisy healthy stream;
- out-of-order delivery;
- duplicate delivery.

---

## 65. Synthetic connection-loss test

Test:

~~~
streaming
↓
network unavailable
↓
local spool
↓
reconnect
↓
replay
↓
deduplication
↓
zero canonical loss
~~~

within configured spool capacity.

---

## 66. Broker and consumer failure tests

Test broker restart.

Test consumer restart.

Expected properties:

- retained unconsumed records;
- clean resume;
- idempotent canonical persistence;
- no duplicate canonical rows;
- no silent loss within configured durability guarantees.

---

## 67. Sampling-rate tests

Example synthetic recipe:

- RPM 10 Hz;
- speed 10 Hz;
- throttle 10 Hz;
- boost 10 Hz;
- temperatures 2 Hz.

Verify measured effective rates are within documented tolerance in healthy synthetic operation.

Then simulate a slow adapter.

Expected:

- critical channels retain priority;
- lower-priority channels degrade first;
- system reports degradation;
- no silent failure.

---

## 68. Live Phase 2 integration test

Synthetic stream should include:

- idle;
- cruise;
- pull;
- deceleration.

Verify provisional detection.

After stop/finalization verify canonical Phase 2 persists the expected pull(s).

---

## 69. Live Phase 3 integration test

Inject a known anomaly such as boost_drop.

Verify:

1. provisional factual event appears live;
2. event is explicitly provisional;
3. session finalizes;
4. canonical Phase 3 runs;
5. final event exists;
6. provenance/reconciliation is understandable.

Run a noisy healthy stream and verify no spurious anomaly alerts.

---

## 70. Database and Alembic migration safety

Current Phase 3 migration head is 0004.

Phase 4 must add new migration revisions without editing applied revisions 0001–0004.

IMPORTANT: do not repeat the previous stale migration assertion problem.

Never scatter hardcoded assumptions like:

~~~
assert version == "0004"
~~~

through unrelated integration tests after creating a newer head.

Migration tests should derive head semantics structurally where possible.

Implement a reusable helper/check that:

- discovers the current Alembic head;
- verifies exactly the expected number of heads;
- compares the database alembic_version to the discovered head;
- can discover the direct parent revision;
- validates the chain.

For Phase-specific semantic testing, a centralized new revision constant is acceptable only when intentionally tied to that migration and updated in the same commit.

---

## 71. Migration acceptance protocol

In disposable TimescaleDB validate:

1. clean upgrade from base to current head;
2. Phase 4 tables/structures exist;
3. downgrade one Phase 4 revision to its direct parent;
4. Phase 0–3 tables remain;
5. only intended Phase 4 structures disappear;
6. re-upgrade to head;
7. repeated upgrade is safe;
8. full downgrade to base according to repository policy;
9. final clean upgrade to head;
10. Timescale extension remains correct;
11. telemetry hypertable remains correct;
12. migration head check matches Alembic metadata.

Do not leave stale expectations after creating a new revision.

---

## 72. Phase 4 domain entities

Introduce only justified entities.

Potential examples:

- LoggingRecipe / recipe version;
- AcquisitionSession;
- AcquisitionSource or Device;
- DeviceCapabilitySnapshot;
- AcquisitionRun;
- bounded ingestion error record if needed.

Avoid entity explosion.

---

## 73. Recipes as code versus database

Make an explicit decision.

Built-in recipes may be versioned code fixtures.

Custom/user-editable recipes, if implemented, require:

- persistence;
- strict validation;
- versioning;
- deterministic hashing;
- no arbitrary expression/code execution.

Document this in an ADR.

---

## 74. Recipe hashing and provenance

Use canonical deterministic serialization.

A collected dataset/session must be able to state which:

- recipe;
- recipe version;
- recipe hash;
- adapter;
- capability snapshot;
- sampling plan;
- achieved rates;
- reconnect count;
- dropped-sample count;
- collector version

produced it.

---

## 75. API surface

Add typed bounded APIs consistent with repository conventions.

At minimum support equivalent functionality for:

### Logging objectives
- list known objectives.

### Recipes
- list recipes;
- get recipe;
- preflight a recipe.

### Acquisition
- create acquisition session;
- get acquisition session;
- start/activate if appropriate;
- stop/finalize;
- abort;
- inspect quality.

### Ingestion
- authenticated bounded telemetry batch ingestion or equivalent streaming gateway.

### Live client
- versioned WebSocket or SSE channel for acquisition status, telemetry snapshot, quality, provisional pull/event, and finalization progress.

Keep routes coherent rather than creating unnecessary RPC endpoints.

---

## 76. Live message types

Version frontend live contracts.

Potential message kinds:

- acquisition_status;
- telemetry_snapshot;
- quality_update;
- provisional_segment;
- provisional_pull;
- provisional_event;
- finalization_status.

---

## 77. Frontend Logging Assistant

Create a setup flow:

1. select known objective;
2. show recipe;
3. show required/recommended/optional signals;
4. select/probe source;
5. show capability matrix;
6. show readiness and limitations;
7. show sampling plan;
8. start acquisition.

No LLM is needed.

---

## 78. Recipe explanations

For each requested signal show why it matters.

Example:

~~~
Boost pressure
Recommended

Used for:
- boost behavior
- pull comparison
- boost drop / overshoot events
~~~

Use factual deterministic copy.

---

## 79. Capability matrix

Display something equivalent to:

~~~
Signal             Requirement     Device      Planned rate
RPM                Required        ✓           10 Hz
Vehicle speed      Required        ✓           10 Hz
Throttle           Required        ✓           10 Hz
Boost              Recommended     ✓           10 Hz
IAT                Recommended     ✓            5 Hz
HPFP               Recommended     ✕            —
Timing correction  Optional        Unknown      —
~~~

Do not imply unavailable channels were measured.

---

## 80. Live frontend states

Show operational states distinctly:

- connecting;
- device connected;
- capability probe complete;
- streaming;
- reconnecting;
- finalizing;
- completed;
- failed.

Distinguish adapter/device connection state from server/broker state.

---

## 81. Real-time quality UX

Show:

- actual rates;
- target rates;
- dropped samples;
- latency;
- connection state;
- buffer state;
- broker/consumer health at an appropriate abstraction.

Warnings should be actionable.

Example:

“Boost sampling rate has fallen to 2.1 Hz. Fast transient boost analysis may be limited.”

---

## 82. Provisional live events UI

Display Phase 2/3 live results with an explicit LIVE / PROVISIONAL badge.

Final canonical results must have distinct semantics.

Do not use diagnosis wording.

---

## 83. Finalization UX

On stop:

~~~
Finalizing session...

✓ Telemetry persisted
✓ Phase 2 complete
✓ Phase 3 complete
✓ Dataset capability assessment complete
~~~

If a stage fails, report it without implying telemetry was lost.

Post-session summary should include:

- duration;
- observations;
- actual rates;
- gaps;
- recipe adherence;
- pulls;
- final factual events;
- capabilities supported by the dataset.

---

## 84. OpenAPI and frontend contracts

FastAPI/Pydantic remains authoritative.

Regenerate TypeScript contracts.

Do not create hand-maintained duplicate API types.

contracts-check must pass.

---

## 85. Unit and contract tests

Add thorough tests for:

### Recipes
- validation;
- version/hash determinism;
- objective mapping;
- required/recommended/optional semantics;
- readiness;
- capability assessment;
- post-log assessment.

### Sampling
- priorities;
- target rate;
- slow adapter;
- timeout;
- rescheduling;
- optional signal degradation;
- jitter;
- actual rate measurement.

### Collector
- start/stop;
- graceful shutdown;
- reconnect;
- spool;
- replay;
- duplicate prevention;
- sequence continuity;
- token handling;
- failure state.

### Stream
- serialization;
- schema version;
- unknown version rejection;
- batch validation;
- duplicate delivery;
- out-of-order delivery;
- consumer retry;
- poison message;
- bounded queue.

### Live analysis
- provisional pull;
- provisional event;
- event closure;
- healthy/noisy stream;
- gaps;
- reconciliation.

---

## 86. Integration tests

Use real Docker dependencies and disposable TimescaleDB.

Required full path:

~~~
synthetic collector
↓
gateway
↓
durable broker
↓
consumer
↓
TimescaleDB
~~~

Verify canonical observations persisted.

Also test:

- temporary gateway disconnect;
- spool replay;
- broker restart;
- consumer restart;
- duplicate delivery;
- out-of-order delivery;
- database temporary failure if practical;
- migration downgrade/re-upgrade;
- acquisition token rejection;
- recipe preflight;
- final Phase 2/3 analysis.

---

## 87. E2E browser scenario

Real-stack deterministic E2E should:

1. use synthetic BMW 335i F30/N55 reference vehicle;
2. choose Performance Pull objective;
3. inspect recipe;
4. inspect required/recommended signals;
5. run synthetic device preflight;
6. verify readiness;
7. start acquisition;
8. observe live telemetry updates;
9. observe effective sample rates;
10. observe provisional pull;
11. observe provisional boost_drop event;
12. simulate temporary disconnect;
13. show reconnect state;
14. continue without corrupting session;
15. stop;
16. finalize;
17. run Phase 2;
18. run Phase 3;
19. verify canonical pull;
20. verify canonical boost_drop;
21. verify post-log capability report;
22. verify provisional badges are not used for canonical final results.

Capture a screenshot artifact.

Also add a degraded-recipe scenario where boost is unavailable and the UI correctly states which capabilities are unavailable.

---

## 88. Performance benchmark

Benchmark the actual streaming architecture with deterministic synthetic telemetry.

Use at least 100,000 observations.

Record:

- observations produced;
- observations accepted;
- observations persisted;
- lost observations;
- duplicate messages received;
- duplicate canonical rows;
- producer throughput;
- gateway throughput;
- broker publish latency;
- consumer throughput;
- DB persistence throughput;
- end-to-end persistence latency;
- p50/p95 latency where practical;
- buffer growth under slowdown;
- reconnect recovery;
- memory where practical.

Do not invent numbers.

Do not turn exact timing into a brittle gate without evidence.

---

## 89. Sustained stream test

Run a bounded sustained stream long enough to expose:

- memory leaks;
- queue growth;
- connection leakage;
- offset problems;
- unbounded buffers.

Keep CI runtime reasonable and document duration.

---

## 90. Observability

Add bounded-cardinality metrics for:

- active acquisition sessions;
- observations received;
- observations persisted;
- stream publish failures;
- consumer lag;
- dropped observations;
- duplicate observations;
- reconnects;
- local spool occupancy;
- live-analysis latency;
- finalization duration;
- detector provisional event counts by bounded category where appropriate.

Never use vehicle/session/pull/event IDs or VINs as Prometheus labels.

Add traces across:

collector batch → gateway → stream → consumer → persistence → live analysis

Preserve correlation/batch identifiers without raw telemetry arrays in spans.

---

## 91. Logging

Structured logs may include:

- adapter class;
- recipe key/version;
- safe counts;
- batch size;
- rates;
- reconnect count;
- queue depth;
- error category.

Do not log:

- raw acquisition tokens;
- VINs;
- huge telemetry arrays;
- full uploaded logs;
- precise location;
- device secrets.

---

## 92. Geolocation

Do not add GPS/precise location collection by default.

Phase 4 does not require it.

---

## 93. Security threat model

Review and test:

- forged telemetry;
- replay;
- stolen token;
- expired token;
- oversized batch;
- malformed schema;
- timestamp abuse;
- queue flooding;
- reconnect amplification;
- broker exposure;
- resource exhaustion.

Acquisition tokens must be:

- high entropy;
- scoped;
- expiring/session-bound;
- revocable;
- never logged;
- not placed in URL query strings unless unavoidable and justified.

Bound:

- session creation;
- request frequency;
- batch size;
- observations per batch;
- concurrent acquisition sessions;
- concurrent live clients;
- recipe size;
- total analysis workload.

Broker must remain internal by default.

---

## 94. Failure behavior

### Database unavailable
Consumer retries safely.
Do not acknowledge offsets as durable prematurely.
Broker retains uncommitted/unprocessed data according to chosen semantics.

### Stream unavailable
Collector/gateway uses bounded spool and visible warnings.
No silent discard.

### Device disconnect
Mark acquisition state.
Attempt bounded reconnect where supported.
Do not infer engine failure.

### One bad signal
Other channels continue if possible.
Mark that signal degraded/unavailable.
Update recipe capability assessment.
Do not unnecessarily abort whole session.

---

## 95. Retention

Do not add automatic destructive canonical Timescale retention unless separately justified.

Broker may use bounded development retention.

Document difference between broker retention and canonical storage.

Timescale remains the long-term analytical source of truth.

---

## 96. Live versus canonical source of truth

Broker = transport/replay layer.

Timescale canonical telemetry = durable analytical source.

Live analysis = low latency, bounded, incomplete, provisional.

Canonical Phase 2/3 = complete persisted event-time data, reproducible, final.

This must be clear in code, contracts, UI, and docs.

---

## 97. Explicitly out of scope

Do not implement:

- advanced Phase 5 analytics;
- longitudinal scoring;
- MCP;
- LangGraph;
- agents;
- free-text objective interpretation;
- RAG;
- vector DB;
- ML anomaly models;
- MLflow;
- feature store;
- BMW proprietary PID mappings without evidence;
- ECU writes;
- actuator control.

---

## 98. Documentation

Add detailed documentation for:

- live acquisition architecture;
- collector;
- adapters;
- current hardware support status;
- stream topology;
- message schemas;
- delivery semantics;
- recipes;
- objectives;
- preflight;
- sampling planner;
- quality monitor;
- spool/reconnect;
- provisional versus final analysis;
- troubleshooting;
- security;
- limitations;
- physical hardware validation procedure.

---

## 99. Physical hardware validation runbook

Write a safe future runbook:

1. connect adapter;
2. probe device;
3. inspect capabilities;
4. use General Health recipe initially;
5. perform stationary/non-performance validation first;
6. verify measured rates;
7. capture diagnostic logs;
8. stop/disconnect cleanly.

Performance testing must be explicitly separated and limited to lawful controlled environments.

Documentation must truthfully state either:

- real Vgate hardware validated; or
- adapter implementation exists, physical Vgate validation pending.

Do not overclaim.

---

## 100. BimmerLink status

Document clearly:

A real BimmerLink export is required before claiming first-class BimmerLink schema compatibility.

Phase 4 should provide the generic mapping architecture needed to add the adapter later.

---

## 101. ADRs

Create strong ADRs for at least:

### Streaming architecture
Document:
- broker selection;
- delivery semantics;
- replay;
- idempotency;
- topics;
- offsets;
- local spool.

### Acquisition lifecycle / recipes
Document:
- recipe model;
- sampling planner;
- preflight;
- capability assessment;
- live provisional versus canonical final;
- collector boundary.

Avoid ADR spam.

---

## 102. Repository context and reusable workflows

Update AGENTS.md.

Consider reusable local skills/workflows for:

- stream contract change;
- logging recipe change;
- migration change.

A logging-recipe change should require:

- rationale;
- availability;
- degraded behavior;
- deterministic synthetic test;
- version/hash review;
- docs.

A stream-contract change should require backward/compatibility review.

---

## 103. Make targets and regression gates

Add clear Phase 4 targets, for example:

- make phase4-acceptance
- make stream-test

Preserve:

- phase3-acceptance;
- Phase 1/2 tests;
- unit coverage;
- contracts;
- security;
- E2E;
- observability.

Phase 4 must not make old gates disappear.

A good verify-cloud shape is conceptually:

~~~
verify-local
phase3-acceptance
phase4-acceptance
security-cloud
~~~

---

## 104. Migration guard in CI

Add a reusable migration-head test/check.

It should fail if:

- multiple unexpected heads exist;
- DB revision differs from current Alembic head;
- chain is broken.

Avoid old hardcoded head IDs throughout the suite.

This is specifically required to prevent recurrence of the Phase 3 0003-vs-0004 CI bug.

---

## 105. Canonical Docker validation

Canonical full validation must include required stream services and workers.

Verify health before integration/E2E.

On failure capture:

- broker logs;
- collector logs;
- consumer logs;
- API logs;
- compose status;
- offset/lag diagnostics;
- Playwright report;
- relevant test output.

Never upload secrets.

The existing workflow may still be historically named “Phase 0 full validation”.

Renaming it to “Canonical Full Validation” is optional only if it will not break branch-protection required-check configuration.

Do not risk required-check settings for cosmetic cleanup.

---

## 106. Golden live scenarios

At minimum implement deterministic scenarios for:

1. healthy normal stream;
2. performance pull;
3. boost-drop pull;
4. temporary network loss;
5. slow adapter;
6. broker restart;
7. consumer restart;
8. out-of-order frames;
9. duplicate frames;
10. telemetry gap;
11. missing recommended signal;
12. missing required signal.

---

## 107. Acceptance — loss and duplication

For a reconnect scenario that remains within configured spool capacity:

- zero canonical observation loss;
- zero duplicate canonical rows.

If spool capacity is intentionally exceeded, any loss must be explicit, counted, documented, and testable.

---

## 108. Acceptance — recipes

For every initial recipe validate:

- rationale for each signal;
- required/recommended/optional semantics;
- capability discovery;
- readiness;
- sampling plan;
- actual post-log quality assessment;
- degraded behavior.

---

## 109. Acceptance — live analysis

Must demonstrate:

- provisional Phase 2 pull;
- provisional Phase 3 factual event;
- explicit provisional status;
- canonical Phase 2 final result;
- canonical Phase 3 final result;
- reconciliation;
- no diagnostic/root-cause statement.

---

## 110. Acceptance — performance

For 100k+ streamed observations report:

- sent;
- received;
- persisted;
- lost;
- duplicate messages;
- duplicate canonical rows;
- throughput;
- end-to-end latency;
- buffer behavior;
- reconnect behavior.

---

## 111. Acceptance — security

Required evidence:

- valid scoped token accepted;
- invalid token rejected;
- expired/closed session token rejected;
- oversized batch rejected;
- malformed schema rejected;
- broker internal/not publicly exposed by default;
- secret scan passes;
- dependency scan passes;
- image scan passes.

---

## 112. Acceptance — observability

Canonical validation must prove:

- metrics endpoint;
- acquisition metrics;
- stream/consumer metrics;
- traces through the ingestion path where supported;
- bounded cardinality;
- broker/worker health;
- observability regression from prior phases still passes.

---

## 113. Local Codex environment

Docker may be unavailable.

Detect it first.

If unavailable, run all non-Docker validation, including repository-equivalent targets such as:

~~~
make verify-cloud
make phase4-acceptance
~~~

Docker-dependent validation must be reported as CI REQUIRED, never locally passed.

---

## 114. Push early

After the first coherent vertical slice:

- commit;
- push to codex/phase-4-streaming-live-acquisition;
- verify remote SHA;
- confirm Actions start.

Do not wait until the entire phase is complete before discovering GitHub publishing or CI problems.

All fixes must stay on the same Phase 4 branch.

Do not create phase-4-fix, phase-4-final, or phase-4-v2 branches unless repository corruption makes it unavoidable.

---

## 115. Pull request

Create exactly one PR.

Base: main

Head: codex/phase-4-streaming-live-acquisition

Suggested title:

feat: add Phase 4 streaming and live vehicle acquisition

Do not merge automatically.

---

## 116. GitHub Actions

Monitor actual commit-tied:

- CI;
- Security;
- canonical full validation.

Do not finish because a push succeeded.

If a repository-caused failure occurs:

1. inspect failed job;
2. inspect logs;
3. identify root cause;
4. fix properly;
5. commit;
6. push same branch;
7. repeat.

Do not weaken assertions just to get green.

Avoid blind sleeps for flaky services; use health checks/readiness/event acknowledgement/bounded polling.

---

## 117. No premature completion report

Do not declare Phase 4 complete while mandatory workflows are:

- queued;
- running;
- red;
- cancelled.

Wait for final workflow results.

---

## 118. Definition of Done — architecture

Complete only when:

- local collector exists;
- read-only adapter abstraction exists;
- synthetic live adapter exists;
- replay adapter exists;
- real generic OBD path exists or concrete documented boundary is implemented responsibly;
- durable streaming path exists;
- stream consumer persists canonical telemetry;
- at-least-once retry is idempotent;
- reconnect works;
- local spool is bounded;
- backpressure is bounded;
- live frontend update path exists.

---

## 119. Definition of Done — recipes

Complete only when:

- LoggingRecipe is a first-class versioned concept;
- deterministic known-objective mapping exists;
- initial recipes exist;
- preflight exists;
- capability discovery exists;
- sampling planner exists;
- actual sample-rate measurement exists;
- post-log capability assessment exists.

---

## 120. Definition of Done — live analysis

Complete only when:

- provisional Phase 2 behavior exists;
- provisional Phase 3 behavior exists where supported;
- provisional status is explicit;
- canonical finalization runs;
- reconciliation works.

---

## 121. Definition of Done — UI

A user must be able to:

1. choose a predefined objective;
2. inspect recipe;
3. inspect required/recommended signals;
4. inspect source capabilities;
5. see readiness;
6. see planned rates;
7. start synthetic/live acquisition;
8. view live telemetry;
9. view actual signal quality/rates;
10. observe provisional pull/event;
11. stop/finalize;
12. inspect final canonical results;
13. inspect post-log capability assessment.

---

## 122. Definition of Done — reliability

Explicitly test:

- network loss;
- reconnect;
- spool replay;
- duplicate delivery;
- out-of-order delivery;
- broker restart;
- consumer restart;
- slow adapter;
- near-full/full spool;
- graceful shutdown.

---

## 123. Definition of Done — migrations

Complete only when:

- new revision(s) exist;
- applied revisions 0001–0004 remain untouched;
- current-head migration check is dynamic/structural;
- downgrade/re-upgrade passes;
- Phase 0–3 schema remains correct after Phase 4 downgrade;
- Timescale extension and hypertable remain correct;
- no stale Phase 3 revision assertion remains.

---

## 124. Definition of Done — quality

Complete only when all relevant items are green:

- backend unit tests;
- frontend tests;
- stream-contract tests;
- collector tests;
- synthetic live tests;
- integration tests;
- migration tests;
- OpenAPI/contracts;
- browser E2E;
- 100k+ benchmark;
- Phase 3 acceptance regression;
- Phase 4 acceptance;
- security;
- observability;
- documentation;
- ADRs;
- CI;
- Security workflow;
- canonical full validation.

---

## 125. Phase boundary

Phase 4 should be able to answer:

- What should I log for this predefined objective?
- Can this source/device provide those signals?
- What polling rates should be used?
- Is the current logging setup ready, degraded, or blocked?
- Is the incoming data good enough?
- What analyses will this dataset support?
- Is a pull provisionally happening now?
- Has a factual irregularity provisionally appeared now?
- Did canonical final analysis confirm/reconcile it?

Phase 4 must not yet answer:

- What do you think is wrong with my car?
- Which component should I replace?
- Which recipe should I generate from arbitrary natural-language intent?

Those belong to later agent/RAG/diagnostic phases.

---

## 126. Final delivery report

Return a report titled:

PHASE 4 DELIVERY REPORT

Include:

### Repository
- branch;
- baseline;
- commits;
- PR URL;
- remote head;
- working tree state.

### Architecture
- collector architecture;
- adapter architecture;
- broker decision;
- topics/contracts;
- at-least-once semantics;
- idempotency;
- replay;
- spool;
- backpressure.

### Hardware
- implemented generic adapter path;
- real physical hardware validation status;
- Vgate vLinker validation status;
- BMW proprietary/enhanced signals intentionally unsupported if unvalidated.

### Recipes
- objectives;
- recipes;
- required/recommended/optional signals;
- preflight;
- readiness;
- capability model;
- sampling planner;
- post-log assessment.

### Live system
- telemetry flow;
- sample-rate monitoring;
- provisional Phase 2;
- provisional Phase 3;
- reconciliation;
- UI.

### Migrations
- previous head;
- new head;
- dynamic head validation;
- downgrade/re-upgrade evidence;
- confirmation that stale migration-literal issue was prevented.

### Reliability
Report real results for:
- disconnect/reconnect;
- spool replay;
- duplicate delivery;
- out-of-order delivery;
- broker restart;
- consumer restart;
- backpressure;
- graceful shutdown.

### Performance
Report actual benchmark values:
- observations sent;
- observations persisted;
- observations lost;
- duplicate canonical rows;
- producer throughput;
- consumer throughput;
- end-to-end latency;
- buffer behavior.

### Testing
- backend tests;
- frontend tests;
- collector tests;
- stream tests;
- integration;
- migrations;
- E2E;
- contracts;
- Phase 3 acceptance regression;
- Phase 4 acceptance.

### Security
- acquisition authentication;
- resource/rate bounds;
- broker exposure;
- scans.

### Observability
- metrics;
- traces;
- stream health.

### GitHub
- CI run ID and result;
- Security run ID and result;
- canonical full-validation run ID and result.

### Explicit deferrals
List:
- Phase 5 advanced analytics;
- MCP;
- agents;
- free-text objective understanding;
- LangGraph;
- RAG;
- ML;
- BMW proprietary PID support not actually validated;
- physical Vgate validation if pending;
- first-class BimmerLink parser until a real export exists.

Only report:

PHASE 4: COMPLETE

and:

PHASE 5: READY

if all software acceptance criteria and actual commit-tied GitHub canonical workflows are green.

If physical Vgate hardware was not available, state separately:

Physical hardware validation: PENDING

This alone does not make the software Phase 4 incomplete if:

- the read-only adapter boundary is implemented;
- transport/protocol behavior is tested with deterministic fake transport;
- synthetic/replay live acquisition is fully validated;
- no unverified physical support is claimed.
