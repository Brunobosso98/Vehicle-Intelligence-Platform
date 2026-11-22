# MLOps control plane runbook

This is a local, controlled, offline operator workflow. It does not deploy a
model or change a serving binding.

## Preconditions

- Use a disposable database for acceptance. Its database name must begin with
  vehicle_test.
- Set ENVIRONMENT=development or ENVIRONMENT=test explicitly. Production is
  denied by policy.
- Use a clean, committed checkout. The manifest SHA must match HEAD.
- Confirm source role, feature/label checksums, training cutoff, reserved
  holdout and evaluation cohort before execution.
- Keep model and detector artifacts under their existing private trusted roots.

The operator CLI is local-only:

    ENVIRONMENT=test vehicle-mlops --help
    ENVIRONMENT=test vehicle-mlops plan --manifest /private/path/manifest.json
    ENVIRONMENT=test vehicle-mlops run --manifest /private/path/manifest.json

Planning is read-only. Execution is not started unless --execute,
--confirm-environment test, and the exact immutable definition
--fingerprint are supplied. A same-task/family active 9D binding is required
for a matched champion comparison.

    ENVIRONMENT=test vehicle-mlops run \
      --manifest /private/path/manifest.json \
      --execute \
      --confirm-environment test \
      --fingerprint <definition-sha256> \
      --champion-binding-id <existing-9d-binding-uuid>

The command accepts only fixed 9B task/9C family catalogs and bounded JSON
manifests. Do not place secrets, VINs, raw telemetry or row-level labels in a
manifest. Exact source, dataset, feature, label/oracle and time-cutoff lineage
is required; rejected or insufficient plans must be corrected at the source,
not overridden.

## Inspect and resume

    ENVIRONMENT=test vehicle-mlops inspect --run-id <run-uuid>
    ENVIRONMENT=test vehicle-mlops resume --run-id <run-uuid> --manifest /private/path/manifest.json
    ENVIRONMENT=test vehicle-mlops reproduce --run-id <completed-supervised-run-uuid>

Resume is read-only by default. A completed logical run returns the original
receipt. To recover, provide --execute, the same environment, exact
definition fingerprint and same incumbent binding. A changed manifest is a
new definition and cannot resume the old run. Expired leases advance the
fencing token and fail closed if artifact registration is uncertain. Inspect
the registry and report checksums before starting a new run; never edit
control-plane rows manually.

`reproduce` accepts one completed synthetic supervised run. It rebuilds the
9B model from the original training cohort in a private temporary directory,
then checks the existing frozen 9G evaluation cohort in read-only mode. It
does not create a pipeline run, model registry version, evaluation record,
proposal or serving change. The held-out scores are only a determinism check;
they do not select a candidate, calibrate a threshold, tune a model or change
the experiment. The command returns a checksummed `ReproductionReceipt` and
exits nonzero if any source, artifact or metric checksum differs.

Each stage has an immutable event receipt. A timeout or process interruption
does not mean a model was activated. Verify vehicle-mlops inspect, artifact
checksum and 9G report lineage before resuming.

## Review a proposal

    ENVIRONMENT=test vehicle-mlops proposal --proposal-id <proposal-uuid>
    ENVIRONMENT=test vehicle-mlops review \
      --proposal-id <proposal-uuid> \
      --proposal-checksum <proposal-sha256> \
      --decision accept \
      --reason "Reviewed dataset, support, applicability and rollback evidence." \
      --execute --confirm-environment test \
      --confirm-proposal-checksum <proposal-sha256>

Review authentication is separately configured with an owner-only JSON file
named by MLOPS_REVIEWER_CONFIG and a separate high-entropy
MLOPS_OPERATOR_TOKEN. The file contains reviewer IDs, the fixed
mlops_reviewer role and token SHA-256 values; do not commit it or put the
token in shell history. Invalid credentials, stale proposal checksums, wrong
role, public environment or missing reason are denied. The append-only review
records identity, role, environment, decision and reason.

APPROVED_FOR_CONTROLLED_REVIEW is a human review result. It is not Phase 9D
approval, activation or rollback.

## Operator decision notebook

Record one review worksheet per proposal. Keep row-level telemetry, labels, VINs,
credentials and private identifiers out of the worksheet; reference immutable
checksums and the local proposal ID only.

- Verify the exact serving candidate and current binding using the established
  Phase 9D inspect/list flow.
- Confirm CI checked the same source SHA as the proposal and no required gate is
  pending, failed or tied to an earlier SHA.
- Read the change log and candidate dossier. Confirm task/horizon or detector
  family, artifact checksum, source role, feature and label definitions, dataset
  checksum, holdout cohort and time cutoffs.
- Review labeled row/session support, abstentions, exclusions, missingness,
  uncertainty and Phase 9G scientific-readiness statuses. Do not treat synthetic
  calibration as real-world validity or unlabeled telemetry as performance data.
- Check champion/challenger cohort identity and comparability. A method-specific
  anomaly score is not an engine-health percentage or diagnosis.
- Verify the current rollback target, active binding, artifact and compatibility
  before any separate 9D action. A Phase 10 readiness plan grants no permission.
- Record stakeholder impact, maintenance-safety implications, unresolved
  limitations, reviewer identity, decision and reason in the authenticated
  proposal review event.
- If a separate 9D transition is authorized later, reference its actual event
  ID and verify the active binding after the transition. Do not infer deployment
  from a passing pipeline or review.

## Release readiness matrix

| State                                 | Evidence                                                              | Serving meaning                           |
| ------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------- |
| `PIPELINE_READY`                      | Frozen definition, source lineage, limits and eligibility checks pass | No evaluation claim or serving permission |
| `EVALUATED_FOR_SYNTHETIC_ENGINEERING` | Registered artifact and frozen synthetic 9G evaluation receipt        | Synthetic engineering evidence only       |
| `REVIEW_REQUIRED`                     | Immutable candidate dossier and matched comparison are persisted      | Human review is required                  |
| `SERVING_APPROVAL_PENDING`            | Review is recorded but no separate 9D approval event exists           | Not approved for serving                  |
| `APPROVED_FOR_CONTROLLED_REVIEW`      | Authenticated reviewer accepted the exact proposal checksum           | Review decision only; no serving change   |
| `NOT_PRODUCTION_READY`                | Default final status for Phase 10 candidates                          | Production is prohibited                  |

No report may use `DEPLOYED` or imply deployment unless a distinct, independently
verified Phase 9D serving event and active binding are present. CI success alone
does not create that evidence.

## Rollback readiness and 9D reconciliation

    ENVIRONMENT=test vehicle-mlops rollback-plan \
      --proposal-id <reviewed-proposal-uuid> \
      --target-binding-id <eligible-historical-9d-binding-uuid>
    ENVIRONMENT=test vehicle-mlops rollback-inspect --plan-id <plan-uuid>

Planning verifies the historical binding event, environment, source role,
artifact, feature/schema compatibility, current active binding and proposal.
The stored plan is hash-bound and read-only with respect to 9D. A stale target
returns STALE or BLOCKED. The separate 9D operator workflow owns any real
rollback; verify its actual event before describing a serving change.

## Monitoring

    ENVIRONMENT=test vehicle-mlops monitor --manifest /private/path/monitor.json
    ENVIRONMENT=test vehicle-mlops --metrics-file /private/path/command.prom \
      inspect --run-id <run-uuid>

Monitoring accepts only a fixed protocol and reads persisted receipts. It does
not make predictions or create evidence. Preserve baseline/comparison windows
and their source role, observed time, effective cutoff, model version, feature
schema, session counts, missingness and abstention counts. No rows produce
NO_OBSERVATIONS. Missing verified labels mean performance and calibration
are UNKNOWN, not zero or pass. Treat source drift, score shift, missingness,
and label-based performance drift as separate findings.

## Failure and security response

| Finding                                              | Safe response                                                                                               |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Feature, label, source or artifact checksum mismatch | Stop. Rebuild the exact canonical source lineage; do not weaken the check.                                  |
| Source role, cohort or temporal leakage              | Reject the run; repair the fixture/protocol and issue a new immutable definition.                           |
| Missing labels or low session support                | Record INSUFFICIENT_SUPPORT; do not synthesize labels or claim performance.                                 |
| Missing/oversized/symlinked artifact                 | Preserve receipts, block proposal, inspect trusted path and permissions, then register a new version.       |
| Lease expiry or interrupted stage                    | Inspect run and stage events; reconcile any 9B/9C registration before retry.                                |
| Monitoring warning without labels                    | Create a human review artifact only; do not activate, retune or rollback.                                   |
| Expired container vulnerability exception            | Do not extend it silently. Refresh images/database, remediate, or obtain a specific dated review before CI. |

For incidents, stop the affected evaluation or review and preserve immutable
receipts before changing anything:

| Incident                                | Stop and inspect                                                               | Safe resolution                                                                              |
| --------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Feature/model/detector version mismatch | Compare the bound version, checksum, schema and artifact receipt               | Re-register a new immutable version from trusted sources; re-plan the run                    |
| Missing, symlinked or changed artifact  | Preserve run/proposal IDs and verify private-root ownership, mode and checksum | Block review; restore the exact trusted artifact or register a new version                   |
| Drift or source-composition warning     | Compare frozen windows, source role, feature version, missingness and coverage | Create a human review proposal; do not retrain, activate or rollback automatically           |
| Low support or excessive abstention     | Check per-window rows, independent sessions, feature quality and exclusions    | Record insufficient support and repair upstream sources; never fill in measurements          |
| Temporal/source-role leakage            | Inspect cutoffs, dataset manifests, source hashes and cohort fingerprints      | Reject the definition and issue a new immutable, disjoint cohort                             |
| Verified outcome labels are absent      | Keep accuracy, recall and calibration `UNKNOWN`                                | Collect authorized verified outcomes through the established process; do not infer labels    |
| Expired security exception              | Inspect the fresh scanner output and dated policy entry                        | Remediate the image or obtain a specific maintainer-reviewed exception; never silently renew |

The isolated acceptance rehearsal creates a test-only candidate through the
existing `vehicle-prediction` CLI, activates it explicitly, plans rollback, and
then invokes `vehicle-prediction rollback` after a simulated fault. It verifies
the restored binding and that a denied repeat has no source-table effects. This
is disposable-database evidence only and does not authorize a real rollback.

Never run cleanup against referenced candidate artifacts. Phase 10 has no
automatic garbage collection. Use only the disposable database and deterministic
fixtures for destructive/recovery rehearsals.

## Acceptance commands

    make test-mlops
    make phase10-acceptance
    make benchmark-mlops
    make mlops-observability
    make phase9h-acceptance
    make verify-cloud

phase10-acceptance round-trips migration 0020, runs DB-backed MLOps
integration, builds deterministic 9A–9G prerequisites, drives all 3 supervised
tasks and all 4 anomaly families, verifies persisted dossiers and artifact
bytes, and emits a benchmark/observability receipt. Without a usable Docker
daemon, database, image, browser, scanner and canonical full-stack gates remain
CI REQUIRED.
