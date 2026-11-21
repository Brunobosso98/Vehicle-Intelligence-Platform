# Phase 10 controlled MLOps platform

Phase 10 is a local operator control plane for reproducible, offline candidate
evaluation. It reuses the existing 9A feature/dataset builder, 9B supervised
registry and trainer, 9C detector registry, 9G evaluation protocol, and 9D
controlled binding history. It adds no web endpoint, public dashboard, cloud
training service, schedule, live-vehicle inference, or vehicle command.

## Placement and data flow

    flowchart LR
      O[Authorized local operator] --> C[vehicle-mlops CLI]
      C --> P[Read-only 9A/9B/9C planner]
      P --> D[(Immutable pipeline definition)]
      C --> R[Leased bounded runner]
      R --> A[9A dataset and lineage]
      A --> B[Existing 9B trainer or 9C fitter]
      B --> M[(Existing immutable model/detector registry)]
      M --> G[Existing 9G offline evaluation]
      G --> H[Same-cohort offline comparison]
      H --> Q[(Immutable dossier and review proposal)]
      Q --> U[Explicit authenticated human review]
      U -. separate authorized action only .-> S[Existing 9D CLI and lifecycle]
      S --> I[Read-only later reconciliation]
      E[Existing 9D prediction receipts] --> W[Retrospective monitor]
      W --> Q

The Phase 10 database stores definitions, runs, state events, stage events,
proposals, human decisions, rollback plans and reconciliation observations.
Candidate binaries remain in the existing trusted 9B/9C artifact stores. Foreign
keys point to their immutable version rows; no binary is copied into the MLOps
database.

## Pipeline contract and state

Definitions use the versioned phase10-definition-v2 contract and canonical
SHA-256 fingerprint. Their identity binds the repository SHA, task/family,
source role, training and evaluation cutoffs, source/dataset/feature/label
fingerprints, a bounded sorted training pull cohort, a disjoint preselected
evaluation pull cohort, oracle checksum, seed, protocol and resource budget.
The planner and executor pass those exact IDs to Phase 9A dataset materialization
and reject a cohort that no longer matches. Definitions are immutable.

Each accepted run executes this fixed DAG:

    stateDiagram-v2
      [*] --> PLANNED
      PLANNED --> CLAIMED
      CLAIMED --> RUNNING
      RUNNING --> COMPLETED
      RUNNING --> INSUFFICIENT_SUPPORT
      RUNNING --> FAILED
      RUNNING --> CANCELLED
      RUNNING --> TIMED_OUT
      RUNNING --> BLOCKED_BY_POLICY

Stages are select, validate, fit, verify_artifact, evaluate, compare, and
report. Stage and run transitions are appended with monotonic event numbers,
a lease, attempt number, and fencing token. The database rejects invalid state
transitions, changed identity, event mutation, and deletion. A dry run is the
default. Execution requires an explicit development/test environment and exact
definition fingerprint. A lease expiry fences the old worker; uncertain
registration is reconciled before any retry. An exact completed replay returns
its existing receipt.

The fixed supervised catalog covers all three 9B next-pull tasks. The anomaly
catalog covers thermal, boost/air, performance and fuel. Planning verifies the
actual 9A source and label rows, role, exact requested cohort, temporal order,
feature schema, support, resource budget, source fingerprints and prior 9G
holdout conflicts before fitting. Anomaly planning binds the 9C method,
reference and frozen synthetic oracle. No caller-supplied executable code,
estimator class or serializer is accepted.

## Evaluation, proposal and serving boundary

Supervised evaluation invokes the established 9B trainer and 9G metrics on a
new predeclared holdout. Anomaly evaluation uses the registered 9C detector
and its frozen family-specific scoring semantics. Comparisons re-read the
actual active 9D binding and registered artifact, then score champion and
challenger on identical eligible rows. Incompatibility produces
NOT_COMPARABLE with a reason and no ranking.

The immutable candidate dossier is embedded in and independently checksummed
with its proposal. It records task/horizon or detector family/method, exact
training and holdout lineage, feature and label checksums, cutoffs, row/session
support, selected training family, holdout metrics and uncertainty, detector
cross-family specificity, artifact checksum, applicability limitations,
intended environment and review state. The dossier cannot grant serving
permission.

Review requires an owner-only local reviewer configuration, a separate
high-entropy token, role, exact proposal checksum, reason and explicit
development/test environment. An accepted review remains
APPROVED_FOR_CONTROLLED_REVIEW. Only a separate authorized invocation of
the existing 9D approve/activate/rollback lifecycle may change serving state.
Phase 10 does not call those methods. Rollback commands create and re-check a
readiness plan; they never perform rollback.

## Retrospective monitoring

The monitor reads existing 9D receipts in repeatable-read, read-only database
transactions. Its protocol freezes binding, source role, vehicle/configuration,
feature schema, baseline/comparison windows, effective/observed time semantics,
feature keys, row/session floors and shift thresholds. It reports counts,
scored/abstained/error rows, missingness, sensor availability, quality
exclusions, source role, feature-source drift and score-distribution shift.

No receipt means NO_OBSERVATIONS, never zero alarms or healthy state.
Without independently adjudicated labels, predictive performance and
calibration are UNKNOWN; neither synthetic labels nor unlabeled real
telemetry may fill the gap. Feature-source drift is reported separately from
true model-performance drift. Monitoring never performs inference, 9E
materialization, agent execution or writes to 9D/9E/9F/9G source tables.

## Boundaries and limits

All execution is synthetic-only until verified real outcome rights and
scientific support are established. Real-vehicle monitoring is retrospective
and read-only. Phase 9B scores are not mechanical failure probabilities.
Phase 9C scores are not engine-health percentages or confirmed diagnoses.
Synthetic calibration is not real-world predictive validity. Real-world
mechanical failure predictive reliability remains NOT_ESTABLISHED.

No public MLOps route, arbitrary training API, automatic production retraining,
continuous inference, customer tenancy, external cloud write, paid AI service,
ECU command, automatic candidate activation or automatic rollback is present.
CI has no serving credentials or write permission. Artifact retention is
non-destructive; Phase 10 provides no garbage collector.

## Phase 9H packaged-runtime compatibility

The Next.js standalone image retains NODE_ENV=production. Predictive operator
authorization is controlled by the explicit platform ENVIRONMENT, all
required server secrets and flags, fixed origin/API host, trusted API peer and
nonempty vehicle allowlist. ENVIRONMENT=development|test permits the narrow
operator BFF when every condition is met; ENVIRONMENT=production remains
fail-closed. The image is not changed to development mode and the UI is not
public. scripts/phase9h-validation.sh exercises the real standalone image,
persisted 9D/9E reads, missing-credential/flag/scope denials, untrusted peer and
production denial.

## Implementation and evidence

Core modules are under apps/api/src/vehicle_platform/mlops/; migration
0020_mlops_control_plane.py is additive. The local CLI is registered as
vehicle-mlops. scripts/evaluate_mlops.py drives real 9A/9B/9C/9G paths in
a disposable database; scripts/check_mlops.py independently checks the
receipt, persisted events, proposal dossier, source digests and registered
artifact bytes. The focused workflow and canonical full-validation workflow
run the exact-head acceptance. Read the operator runbook and acceptance report.
