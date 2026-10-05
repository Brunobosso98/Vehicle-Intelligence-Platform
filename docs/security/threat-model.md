# Initial threat model

Phase 0 is a localhost engineering stack, without accounts or vehicle commands. It is not an
Internet deployment. DB credentials in .env.example are public local examples, never production credentials.

| Threat                               | Status              | Mitigation / next boundary                                                        |
| ------------------------------------ | ------------------- | --------------------------------------------------------------------------------- |
| Secret leakage                       | mitigated           | gitignore, redacted scans, no credentials in logs/errors/client bundles           |
| Dependency compromise / supply chain | partially mitigated | locks, release age, Dependabot, audits/scans; future signed provenance            |
| Injection                            | partially mitigated | parameterized SQL; strict bounded CSV and stream validation                       |
| Broken authorization                 | future phase        | authentication/authorization before public deployment or personal vehicle records |
| Malicious log/file input             | partially mitigated | bounded uploads; duplicate/shape/formula/encoding/finite-value validation         |
| Exposed observability                | partially mitigated | loopback published ports; unauthenticated local profile must never be exposed     |
| Insecure containers                  | partially mitigated | non-root apps, read-only FS, no capabilities, health checks and image scans       |
| Prompt injection                     | future phase        | source trust labels, data/instruction separation and adversarial tests before RAG |
| MCP tool abuse                       | future phase        | least privilege, read-only tools, audited tool authorization before agents        |
| Unsafe automotive actions            | mitigated           | no control endpoints; permanent architectural safety boundary                     |
| Sensitive future telemetry           | future phase        | privacy, access controls, retention and redaction before collection               |

Production additionally requires auth, TLS, managed secrets, backup/restore validation, network policy,
rate limiting, privacy and retention decisions. Do not infer production readiness from Phase 0 quality.

# Phase 4 acquisition threats

Acquisition credentials are high-entropy, session-scoped, stored only as SHA-256 hashes, expire, and are revoked on stop. They are accepted only in the Authorization header and never query strings or logs. Invalid, expired, and closed-session credentials fail before broker publication. Batch schema, bytes at the HTTP server, observation count, timestamps, signal identifiers, session count, collector queues, retry attempts, spool bytes, and live-client duration are bounded.

Forged telemetry remains untrusted evidence rather than a vehicle command. Stable message receipts and canonical sample IDs contain replay and duplicate delivery. Event time is preserved rather than rewritten, and timestamps outside the abuse window are rejected. Kafka has no host-published port, auto-topic creation is disabled, and the consumer acknowledges offsets only after durable database commit. Broker/database outage produces retries and visible lag/spool state rather than silent loss. No GPS, VIN, raw token, ECU-write command, or actuator surface is carried in stream messages.

## Original Phase 4 local resource budgets

The API enforces constant-memory, per-process acquisition request budgets: a burst of 100
requests replenished at 100/second, and ten creation requests replenished at ten/minute.
Independent counters cap 64 simultaneous acquisition/analysis requests, ten live SSE clients,
and four expensive analysis/analytics requests. Counters release on normal completion,
disconnect and cancellation. Excess work receives the normal correlated error envelope with
HTTP 429 and `Retry-After`; control paths and health endpoints retain their normal behavior.
These complement the serialized ten-valid-collector-session DB limit, 500-observation wire batch, 8 producer
publication slots, bounded live windows, query limits and 500k-observation analysis selection.
No IP/token/vehicle dictionaries or Prometheus identity labels are allocated by the budgets.

Expired credentials release collection capacity while remaining rejected; canonical records are
preserved. Stopped/finalizing sessions release collector capacity and finalization shares the
expensive-analysis concurrency budget. A disposable database test verifies full capacity, expiry,
one replacement, continued rejection of excess valid sessions and HTTP 401 without new samples.

The limits govern this local one-process deployment. They are not distributed account quotas,
Internet perimeter defense or authorization; scoped ingestion credentials remain mandatory.
Tests exercise burst/refill, independent concurrency saturation, cancellation release,
unaffected health/lifespan and real disposable-DB excess SSE clients plus recovery.

The collector treats HTTP 429 as a retryable gateway condition, retaining bounded backoff and
durable spool behavior. Authentication/schema rejection remains explicit. Heartbeat rate rejection
is reported safely and never acknowledges or deletes pending telemetry.
