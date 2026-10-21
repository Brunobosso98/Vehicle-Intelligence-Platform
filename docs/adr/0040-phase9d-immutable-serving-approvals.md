# ADR 0040: Phase 9D immutable serving approvals and snapshots

Status: accepted for Phase 9D.

## Context

An offline accepted model or detector is not automatically approved for service. Serving also
needs a stable record of exactly which checksum, task/family, source role, environment, scope and
review were authorized, plus a deterministic rule for revocation and in-flight requests.

## Decision

Add an immutable serving binding tied to one exact registered version and artifact checksum.
Record approval, activation, supersession, revocation and rollback as append-only events. Resolve
current state from ordered events while serializing slot transitions. Each inference captures its
active binding and activation event before input lookup. New requests and receipt replays re-check
revocation; an already admitted inference may finish on its captured activation snapshot. Rollback
appends an event to restore a prior approved binding and never edits history.

## Consequences

- Offline evaluation and service approval remain separate decisions.
- Receipts can identify the binding event that authorized their request.
- Migration `0016` and database triggers protect binding/event immutability; migrations require a
  disposable downgrade/re-upgrade compatibility check.
- The serving scope is fixed to controlled engineering data, not tenant ownership.

## Alternatives considered

- **Infer service eligibility from candidate/accepted lifecycle:** rejected; offline status is not
  a serving authorization.
- **Store a mutable `active` flag:** rejected; it loses the operator's transition history and makes
  in-flight behavior ambiguous.
- **Re-evaluate latest binding during scoring:** rejected; a transition midway through a request
  could change which artifact the request is authorized to use.
