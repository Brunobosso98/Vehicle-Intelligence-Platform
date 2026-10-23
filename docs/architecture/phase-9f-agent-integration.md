# Phase 9F agent integration

Phase 9F lets an explicitly authorized Phase 7 agent run read selected, verified Phase 9E
evidence. It adds no predictive access to ordinary agent questions. The feature is restricted to
development and test environments and an operator-selected vehicle allowlist. Production and
unauthenticated MCP transports fail closed.

## Request and evidence flow

```text
operator question + explicit selected 9E evidence IDs
  -> X-VIP-Prediction-Agent-Capability and vehicle allowlist
  -> intent check for an already recorded prediction or anomaly
  -> separate authenticated MCP prediction token and read scope
  -> exact evidence ID + vehicle/session/pull scope
  -> pure 9E source revalidation (no new audit or inference)
  -> bounded typed MCP summary
  -> run-local evidence IDs, structural claim validation and fixed rendering
  -> public AgentRun snapshot + private exact-lineage row
```

The predictive MCP tool is omitted from `tools/list` for ordinary `mcp:read` tokens. Direct calls
also require `mcp:prediction-evidence:read`, the controlled feature flag, and an allowlisted
vehicle. Its token is distinct from the ordinary MCP token and the operator capability. The MCP
transport must be authenticated Streamable HTTP; stdio and production are rejected.
The operator capability and allowlisted vehicle are rechecked immediately before each selected
read. The in-process `AgentService.revoke_prediction_access()` action denies later reads; an
already admitted read may finish under the current-run snapshot policy. There is no public revoke
route.

`Ask` requires a bounded, explicit set of evidence UUIDs whenever predictive evidence is enabled.
The request must describe a recorded result. Methodology questions, ordinary vehicle questions,
and broad summaries do not read 9E evidence. Plain recorded-result lookups use deterministic
routing and application-authored Portuguese templates. Interpretive requests select only the
matching performance, thermal, or fuel/air/boost specialist. No provider chooses which evidence
may be opened.

## Scope and semantics

The adapter calls `PredictionEvidenceService.read_verified` with the selected vehicle. That path
revalidates the immutable 9E source records, cutoff, schema, and artifact availability without
appending a 9E verification audit or rerunning 9D inference. A foreign vehicle, mismatched pull or
session, unsupported schema, incomplete source, abstention, unavailable artifact, or exceeded run
budget yields a bounded error or data-gap answer.

9B `NEXT_PULL` remains a versioned engineering-label classification about the next compatible
pull; it is not observed future telemetry or a calibrated failure probability. 9C
`AFTER_PULL_OFFLINE` remains a retrospective statistical deviation on an observed pull; it is not
a diagnosis. Both scores preserve their separate units and thresholds. A same-pull pair requires
distinct 9E evidence and receipt IDs, one matching FeatureSet and pull, verified complete/high
quality sources, and both horizons. The rendered statement calls this a shared snapshot, not
independent corroboration, causal evidence, or combined confidence. Predictive answers have low
confidence.

## Evidence admission matrix

| 9E integrity | Completeness | Status, quality, artifact | Allowed answer |
| --- | --- | --- | --- |
| `VERIFIED` | `COMPLETE` | `READY_SCORE`, high quality, artifact `VERIFIED` | Fixed, exactly bound 9B model-classification or 9C statistical-outlier statement with its horizon, threshold, source role and cutoff. |
| `VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE` | `COMPLETE` | `READY_SCORE`, high quality, artifact `UNAVAILABLE` | Historical recorded-output statement with an explicit no-current-reproduction limitation. |
| Accepted integrity | `PARTIAL` or `ABSTAINED` | Any status or quality | `DATA_GAP` answer only; no score or decision claim. |
| `FAILED_SOURCE_MISMATCH` or `NOT_VERIFIABLE` | Any | Any status, quality or artifact | No affirmative numerical/model claim; return a bounded unavailable or data-gap result. |
| Accepted integrity | `COMPLETE` | Low/degraded quality, non-`READY_SCORE`, or missing score | `DATA_GAP` answer only. |

The two accepted integrity states are enumerated in `grounding.py`; completeness, quality and
status checks run before any result renderer. A real-vehicle wording request over a synthetic or
imported source is a data gap. The 9B and 9C renderers separately require their exact horizon, task
or family and typed facts. Tests cover both accepted source states, partial/abstained gaps,
unavailable evidence, wrong horizons and non-finite scores.

Only the compact typed summary enters the run-local evidence registry. The registry projection is
versioned independently from the source bundle. Source evidence, receipt,
FeatureSet and exact source-scope IDs are mapped from the generated run-evidence UUID in
`agent_prediction_evidence_links`, in the same transaction that saves the public run snapshot.
The link table is agent-owned, is not exposed by API routes, and is deleted with its agent run.
Public evidence fingerprints and claim citations use run-local IDs only.

## Persistence and compatibility

Migration `0018_agent_prediction_lineage` adds one private row per predictive run-evidence item.
It does not alter 9B, 9C, 9D or 9E source records. Previous AgentRun snapshots remain valid:
prediction limits are additive with a zero default, and predictive runs record
`supervisor-v4`; existing runs retain their prior supervisor versions. OpenAPI and generated TypeScript
contracts include the explicit ask fields and operator capability header.

The source of truth remains 9E. The AgentRun public JSON schema has no field for private 9E source
identifiers, so the narrow run-owned table is required to preserve auditable exact lineage without
adding those identifiers to provider input or public snapshots. It is an audit mapping, not a copied
prediction manifest; it stores source role, task/family, horizon, cutoff, model/detector versions,
integrity, completeness, artifact availability, and projection version.

## Bounds and failure behavior

- Maximum four selected source bundles per ask, with a separately configured per-run read cap of
  one to four (default two).
- Existing agent MCP, provider, evidence, byte and timeout budgets still apply.
- Predictive access requires both 9D and 9F controlled flags, three distinct high-entropy
  credentials across the operator and MCP boundaries, and an explicit allowlist.
- 9F may only read. It cannot materialize bundles, approve a model/detector, start collection,
  request a new inference, control a vehicle, or write an ECU.
- A provider cannot relabel a statistical/model result as a measured observation. The application
  checks each template, binding, horizon, task/family, score, threshold, lineage, and source role
  before rendering.
- Metrics record bounded authorization outcomes, result type/horizon/source role/integrity/
  completeness/status, grounding outcome, and duration. Vehicle/session/pull/evidence/receipt IDs,
  scores, questions and hashes are excluded from labels and span attributes.

See the [security boundary](../security/threat-model.md#phase-9f-agent-prediction-integration),
[operator runbook](../runbooks/prediction-agent-integration.md), and
[acceptance description](../validation/phase-9f-acceptance.md).
