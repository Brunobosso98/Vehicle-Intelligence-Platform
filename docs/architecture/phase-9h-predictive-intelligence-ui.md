# Phase 9H predictive intelligence UI

Phase 9H is a browser interface for historical Phase 9D receipts, Phase 9E safe evidence,
existing Phase 9F links, and the static Phase 9G synthetic research summary. It does not infer,
train, materialize evidence, verify evidence with the audit-writing endpoint, execute an agent,
promote calibration, monitor vehicles, or control an ECU.

## Data flow and boundaries

```text
browser session cookie
  -> Next.js /api/predictive/* (server-only, no-store)
  -> exact configured API origin + fixed GET route
  -> 9D vehicle-scoped read history/detail
  -> 9E GET safe evidence projection, after receipt/vehicle scope check

Next.js static Phase 9G JSON -> sanitized research view (no database fetch)
Next.js fixed synthetic fixture -> explicitly labeled demo (no 9D/9E request)
```

The generic `/api/domain/[...path]` proxy remains available for unrelated product routes and
rejects normalized aliases for the private prediction namespace before forwarding. The predictive
BFF does not accept a target URL, arbitrary upstream route, user authorization header, or a
state-changing upstream method. Private responses are bounded to 1 MiB, GET-only, manually reject
redirects, use an eight-second abort budget, and carry `private, no-store` headers.

## Operator authorization

There is no user/tenant identity or owner authorization in this platform. The controlled
development/test boundary therefore requires an explicitly enabled operator credential, a
separate session MAC secret, the existing 9D bearer, a fixed browser origin, and an explicit list
of no more than twenty vehicle UUIDs. Each vehicle is allowlisted both by Next.js and 9D. This is
a restricted engineering dataset grant, not vehicle ownership or customer authorization.

The dedicated login compares a high-entropy credential in constant time and applies a five-attempt
per-minute process limit. Successful login issues a 30-minute random opaque cookie whose expiry and
MAC are checked against a bounded server-side session registry. The cookie is HttpOnly,
SameSite=Strict, scoped to `/api/predictive`, and Secure for HTTPS or when explicitly configured.
Login and logout require the configured exact Origin (or same-origin Referer); logout also requires
the session CSRF token. A successful new login revokes an older valid session. The UI clears its
private state on logout, explicit expiry, a 401 scope failure, and vehicle changes.

`predictiveEnabled()` returns false in production regardless of supplied secrets or flags. It also
fails closed unless both the existing 9D service and the independent UI operator boundary are
configured. Sessions are process-local by design and are only suitable for one controlled
development/test runtime; restart invalidates all sessions.

## Safe read contract

The API read index is scoped by the authorized `vehicle_id`, sorted by immutable creation time and
receipt UUID, limited to twenty rows per request and 500 rows per operator history. It joins the
original pull/session and captured/current binding events, verifies the persisted receipt body
against the stored result columns, and runs in a PostgreSQL read-only transaction. Receipt detail,
evidence, and AgentRun context all bind to the same allowlisted vehicle and exact receipt. Unknown
and out-of-scope vehicles are nondisclosing 404 responses.

The BFF validates the exact schema version and projects only supported result fields. It omits
9D lineage, raw feature matrices, private fingerprints, 9E source node identifiers/checksums and
the evidence graph. Curated 9E fact IDs, keys, values, types, quality, gaps, claims, integrity,
completeness, cutoff and limitations remain available; sensitive-looking fact keys are redacted.
It never calls the 9E materialize or verify POST routes. Historical binding state is displayed as
captured and current; revocation does not rewrite the decision or reactivate a binding.

## Scientific presentation

9B uses `NEXT_PULL`; the exact engineering-validation score and original frozen threshold are
shown as scores, never probabilities. 9C uses `AFTER_PULL_OFFLINE`; each detector/family/source
series has its own scale and threshold markers. Missing scores remain missing. Abstentions are
unavailable evidence, not zero, normal, or healthy readings. Source role, quality, cutoff, model or
detector version, evidence integrity and completeness remain visible.

The 9G view is a versioned static synthetic-only research summary, separate from the selected
vehicle. It is not read from per-vehicle prediction routes and cannot be served to 9D. Real-world
predictive validity and calibration remain `NOT_ESTABLISHED`. The demo is a separately labeled
static fixture and is never a fallback for unavailable or empty real history.

## Network and cache policy

Compose attaches API and web to the dedicated `predictive_bff` internal network with fixed
addresses. The API's 9D trusted-peer list includes only that web address plus loopback for local
operations. The BFF accepts only a simple API origin whose host is explicitly allowlisted, builds
paths from fixed route templates and UUIDs, follows no redirects, and uses server-only bearer
injection. The page has no private server-rendered props; session and data routes are dynamic and
uncached. No bearer is placed in browser state, HTML, URL, logs, or browser requests.

## Deferred authorization

Shared deployments remain blocked until the platform has verified user identity, per-owner vehicle
grants, durable shared sessions, and deployment-level secret/network controls. This phase does not
claim any of those capabilities.
