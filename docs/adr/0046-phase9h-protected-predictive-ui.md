# ADR 0046: Controlled server-side predictive UI boundary

Status: accepted for implementation on the Phase 9H branch.

## Context

The platform has an existing Next.js generic domain proxy and a development/test-only 9D operator
bearer, but no production user identity or per-owner vehicle authorization. Direct browser access
to 9D/9E would expose private predictions to arbitrary visitors, and the generic proxy is not an
authorization boundary. Phase 9H needs source-exact historical views without introducing public
tenancy or new prediction/evidence writes.

## Decision

- Add a Next.js server-only, fixed-origin, GET-only BFF guarded by an independent operator
  credential, fixed browser Origin, short-lived MACed HttpOnly session, CSRF token, process limits,
  explicit vehicle UUID allowlist, and fail-closed development/test feature fences.
- Require the API to independently allowlist each vehicle and preserve its existing 9D peer/bearer
  controls. Run the BFF and API on a private Compose network; do not trust forwarded IP headers.
- Add a bounded, read-only 9D receipt history projection and exact vehicle/receipt detail,
  evidence, and AgentRun-context reads. Keep 9E materialization and verification POSTs out of the UI.
- Deny predictive namespace aliases through the generic proxy while preserving existing unrelated
  domain operations.
- Keep synthetic demo and static 9G research data explicit and separate from persisted vehicle
  results. Preserve source scores, thresholds, roles, horizons, cutoffs and limitations.
- Keep all predictive functionality disabled in production until platform identity and ownership
  authorization are implemented.

## Consequences

The controlled test operator can explore immutable persisted history with exact provenance and no
prediction-source writes. The app gains a new operational credential and internal network route,
but not a customer login, tenant model or ownership claim. Sessions are process-local and are
therefore limited to one development/test runtime. Production predictive routes remain unavailable.

## Alternatives rejected

- Sending the 9D bearer from React: rejected because browser bundles/network requests expose it.
- Reusing `/api/domain/*` for prediction access: rejected because it forwards arbitrary paths and
  client authorization headers without vehicle scoping.
- Public demo fallback when real data is unavailable: rejected because it confuses synthetic
  values with stored vehicle decisions.
- Calling 9E materialize/verify or starting a 9F run from the workspace: rejected because these
  operations write audit/source state or execute agent work.
- Enabling prediction screens in production with only a local operator token: rejected because
  it does not establish user identity or vehicle ownership.
