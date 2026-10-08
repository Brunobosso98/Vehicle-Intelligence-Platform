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

## Phase 6 MCP boundary

The MCP allowlist contains only deterministic reads. There is no SQL, file, network, shell, OBD
or ECU passthrough. Adapter calls use read-only transactions and cannot persist analytics/capability
results. An opaque provisioned reader token and SDK scope enforcement protect HTTP. Stdio trusts
the process owner. Token expiry and constant-time verification, sanitized tool errors, bounded
requests/results, context checks, execution/query deadlines and concurrency admission limit abuse.
Host/Origin validation and loopback publication protect local discovery from DNS rebinding.
All repository vehicles are readable to the provisioned reader; tenant ACLs and token issuance
are not implemented. Production requires operator-managed HTTPS/secrets/database access. Tokens
never enter discovery, tool metadata, logs or trace attributes. Telemetry text/metadata is evidence,
not instructions to execute; future agents must preserve this trust boundary.

## Phase 7A agent boundary

Agent questions and MCP-returned metadata are untrusted. The model receives only discovered,
validated read-only tools scoped to one vehicle. Code enforces tool/argument/byte/time/concurrency
budgets, nested ownership, current-run evidence references and exact numeric/unit bindings.
It cannot issue SQL, filesystem, shell, arbitrary HTTP or vehicle commands. MCP credentials and
provider keys remain server-side; exact configured secrets are redacted from public state/events.

Model prose is not streamed before validation. React renders public content as text; no executable
HTML or Markdown is accepted. Fixed application templates separate observations, associations,
hypotheses and insufficient evidence. Claims about mechanical causation or unsupported diagnosis
are rejected. Prompt injection in modification notes never grants a capability.

Agent-owned SQL persistence stores bounded public runs/audits/events, not telemetry dumps, SDK
response objects or private reasoning. The application still lacks end-user authorization; vehicle
UUID checks establish context isolation within the existing trusted operator deployment, not tenant
ACLs. The MCP reader token retains its documented repository-wide scope. See the
[agent runbook](../runbooks/grounded-agent.md) for deployment limits and recovery.
