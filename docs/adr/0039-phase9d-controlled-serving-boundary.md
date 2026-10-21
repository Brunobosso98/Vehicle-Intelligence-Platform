# ADR 0039: Phase 9D controlled serving boundary

Status: accepted for Phase 9D.

## Context

The Phase 9B and 9C registries contain offline-evaluated artifacts, while the platform's existing
vehicle API does not provide user, tenant, or ownership authorization. Exposing predictions on the
ordinary API would turn local operator access into an unjustified public-serving claim.

## Decision

Add a separate `/api/v1/prediction-service` surface that is disabled by default, restricted to
development/test, guarded by a high-entropy bearer token and an allowlisted private/loopback peer,
and bounded before body parsing or database/model work. Do not trust forwarded addresses. Keep the
operator credential out of URLs, request bodies, cookies, logs and response metadata. Production
enablement is rejected. This service does not add user accounts or vehicle ownership grants.

## Consequences

- A controlled local operator can serve reviewed versions without implying public or production
  readiness.
- Any shared, hosted or multi-tenant deployment requires a future platform authorization design.
- The service stays unavailable when its flags or secret are missing or invalid.

## Alternatives considered

- **Use existing vehicle or acquisition routes as authorization:** rejected; neither identifies a
  prediction operator nor establishes ownership.
- **Serve under the ordinary public API:** rejected until platform identity and ownership checks
  exist.
- **Trust `X-Forwarded-For`:** rejected without an explicit trusted-proxy chain.
