# ADR 0044: Controlled Phase 9F prediction evidence in the agent

Status: accepted; implementation and exact-head validation are tracked on the Phase 9F pull
request.

## Context

Phase 9E can verify a historical 9D receipt, but the existing agent and MCP layers do not consume
that evidence. Adding a general-purpose prediction tool to the normal reader would let ordinary
vehicle questions access predictive records and would expose immutable source identifiers to the
provider and public AgentRun snapshot.

## Decision

- Keep predictive reading off by default and allow it only in development/test with a configured
  vehicle allowlist.
- Require an explicit operator capability and a separate high-entropy MCP token carrying
  `mcp:prediction-evidence:read`. Keep the tool hidden from and unavailable to ordinary MCP readers.
- Open only caller-selected 9E evidence IDs after deterministic intent classification. Keep simple
  recorded-result answers in application-owned renderers and route interpretation only to the
  relevant existing specialist.
- Revalidate the frozen 9E source through a pure read path. Do not run inference, create a 9E
  bundle, append a 9E audit, or initiate telemetry collection from the agent.
- Use run-local evidence identifiers publicly and persist exact 9E lineage in an agent-owned
  private table. Preserve 9B `NEXT_PULL` and 9C `AFTER_PULL_OFFLINE` as distinct horizons.
- Treat a same-pull model/anomaly pair as descriptive association only when both bundles point to
  the same pull and FeatureSet; never present it as independent corroboration or a causal result.

## Consequences

Operators can ask a grounded agent about selected historical prediction records in a controlled
environment. Existing agent snapshots need no rewrite. Public citations remain run-local while a
durable private mapping supports audit. Deployment has three explicit authorization/configuration
boundaries and an additional migration. Provider interpretation remains bounded by existing
specialist policies and application claim validation.

The feature is not production authorization, customer consent, tenant isolation, vehicle diagnosis,
accuracy evidence, or a vehicle control path. Real-vehicle accuracy remains unclaimed until a
separate approved validation program exists.

## Alternatives considered

- **Expose the 9E tool to every MCP reader:** rejected because ordinary factual questions should
  not trigger predictive reads and the general token is broader than the new capability.
- **Pass original 9E IDs into public AgentRun evidence:** rejected because source lineage must stay
  out of provider-facing/public evidence while still supporting exact audit.
- **Verify through the 9E audit endpoint:** rejected because a read-only agent query should not
  mutate the 9E verification log.
- **Combine a 9B and 9C result into a confidence vote:** rejected because both can derive from one
  shared FeatureSet and do not provide independent corroboration.
