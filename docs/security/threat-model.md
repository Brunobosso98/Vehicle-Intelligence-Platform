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

## Phase 7B investigation and adaptive logging

| Threat                                                | Boundary and check                                                                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Invented signal or provider-authored recipe           | The provider returns closed semantic roles and gap categories. Code maps only canonical keys and selects immutable Phase 4 catalog recipes; invalid roles and cross-run evidence IDs fail validation.                                                                                                                                                        |
| Prompt or recipe injection from metadata              | Vehicle and modification text is evidence, never an instruction source. Public hypothesis wording is application-owned. No model output enters a PID, Hz, SQL or collector command.                                                                                                                                                                          |
| Unsafe or overbroad capture                           | Phase 7B offers no remote start, actuator, ECU write or free-form acquisition endpoint. The selected Phase 4 recipe and local read-only preflight bound signals, rates, duration and modes. The operator must start the collector explicitly.                                                                                                                |
| Forged source capability                              | A source report needs the separate operator token and active vehicle configuration. OBD reports accept only standard read-only adapter channels and its 12 request/s ceiling. Reports are operator-authenticated claims, not cryptographic device attestations; the collector independently preflights before capture.                                       |
| Approval bypass, stale approval or replay             | Approval binds plan version, exact recipe hash and fresh source snapshot. A changed source or recipe invalidates approval. CAS updates and row locks reject stale mutations; duplicate approval and session link return the existing result.                                                                                                                 |
| Cross-vehicle, cross-configuration or forged callback | The session link checks canonical vehicle, effective configuration, adapter, source reference, finalized state, recipe key/version/hash and capture start after approval in one locked transaction. A bare callback or client-supplied plan state cannot create a link.                                                                                      |
| Planning loops and resource exhaustion                | Hypotheses, gaps, needs, events, versions, cycles, request bodies, concurrent plans and SSE clients have fixed ceilings. One capture cycle and one follow-up AgentRun are allowed per plan.                                                                                                                                                                  |
| Provider keys, operator token and question privacy    | Provider/MCP/operator credentials stay in server configuration or operator input memory; API errors and structured logs omit values. Investigation question, hypotheses and outcomes persist as bounded personal vehicle records in the local database. This deployment has a single operator token, not per-user ACLs or a public privacy/retention policy. |
| SSE without authorization                             | Every investigation read, mutation and SSE request checks the operator header with constant-time comparison. The same-origin web proxy forwards the header without storing it.                                                                                                                                                                               |

The Phase 7B acceptance suite checks the token, stale version/hash, source mutation, cross-vehicle
read/link, duplicate linkage, unknown OBD channel and bounded follow-up. A production Internet
deployment still requires user identity, per-vehicle ACLs, TLS, managed secrets and retention policy.

## Phase 7C supervisor and specialists

| Threat                                            | Application boundary                                                                                                                                                                                                                  |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Specialist impersonation or permission escalation | Application assigns run, vehicle, role and version; immutable registry filters tool schemas and checks every requested name before MCP execution. Provider output cannot choose another role or extend permissions.                   |
| Malicious metadata or tool instructions           | Routing and role policies are application instructions; vehicle, configuration, modification and tool content remain JSON data. Fixed grounded templates render public findings.                                                      |
| Cross-run, vehicle or configuration injection     | Current-run evidence ownership, nested MCP identity, session/pull scope and Phase 7A temporal configuration validation apply before findings or synthesis. Each run owns its cache.                                                   |
| Sibling evidence leakage                          | Domain tasks receive one frozen shared evidence snapshot plus their own tool results. They never receive sibling messages or later sibling findings. Only the Supervisor aggregates validated results.                                |
| Forged conflicts or arbitrary diagnosis           | Conflict IDs must reference validated findings from different specialists; factual disagreement and competing mechanisms must satisfy code predicates. Conflicting mechanisms preserve ambiguity and the existing investigation path. |
| Resource exhaustion and cancellation races        | Parent and per-role turns, calls, telemetry, bytes, time, concurrency and retries remain bounded. Siblings are cancelled and drained. A writer lock and durable cursor reconciliation protect SSE sequence allocation.                |
| Unreliable telemetry interpreted as a cause       | Data Quality runs first; missing RPM, unreliable relevant sampling, dropout, stuck signals and unavailable quality fail closed. Regular sub-target sampling and unrelated quality events remain explicit limitations.                 |
| Unapproved acquisition                            | Supervisor recommendations use the existing Phase 7B operator token, version/hash approval, source checks and one capture cycle. They never start acquisition or send vehicle commands.                                               |

Deterministic fault scenarios inject provider failures and hostile output through the existing provider
seam while using the production graph, actual MCP and disposable PostgreSQL. Internet deployment
still has the same Phase 7A/7B identity and tenant ACL limitations. See
[supervisor architecture](../architecture/phase-7c-specialist-agents-supervisor.md) and
[runbook](../runbooks/supervisor-specialists.md). Phase 7D owns real-model adversarial evaluation.

## Phase 7D operator diagnostics

Explicit `--diagnostics` captures sanitized public structured model input/output
and MCP arguments/results for the disposable controlled evaluation fixtures.
Traces remain under ignored local validation artifacts and do not enable
production request logging. Configured provider, MCP and investigation tokens
are redacted before persistence. Full SDK/transport objects, authorization
headers, private reasoning items and reasoning summaries are excluded; malformed
unstructured output is hashed. Failed proposals remain untrusted diagnostic data,
never published findings or executable recipes. Fixed validation-rule codes and
case/sequence correlation support reconstruction without exposing secrets.

## Phase 8 documentary knowledge boundary

Retrieved source text has no authority over tools or application policy. Operator-reviewed immutable
source snapshots carry verification and trust; unverified/quarantined/rejected/community sources do
not support normative claims. Application-owned specialist topic allowlists, bounded calls/results,
current-run evidence ownership and exact quotation/numeric validation constrain documentary output.
Injection indicators in source/document/chunk metadata are quarantined at retrieval. Pattern matching
is defense in depth, not a complete prompt-injection detector; runtime tool policy remains decisive.

The controlled downloader validates public DNS addresses and pins its socket to an approved IP while
verifying the original TLS hostname. Every redirect is revalidated; only bounded HTTP(S)/MIME content
is accepted. Private/loopback destinations, executable/archive signatures, path traversal and unsafe
symlinks are rejected. PDF extraction uses a clean child process with CPU/memory/page/character/time
limits; it does not infer diagrams or run embedded actions. Parser dependencies are pinned.

Vehicle scope derives from MCP, including session-effective configuration and modification intervals.
The caller cannot override engine/tune filters. Cross-engine mismatches are excluded; unknown tune,
part or hardware metadata cannot become an exact normative match. Retrieval audit is vehicle-scoped.
The existing local/operator trust boundary still applies; Phase 8 does not add multi-tenant identity.

Copyrighted full documents and embeddings remain outside public API/export and public Git. Citations
contain bounded excerpts and provenance. Embedding reservations/cache share a durable cumulative
USD 2 ledger; source text, API keys and provider exception bodies must not enter logs/traces/UI.
Atomic index publication prevents an interrupted ingestion from replacing the complete live corpus.
The exact local `.env` path holds operator-supplied credentials and is excluded from the directory
secret scan; the gate fails if Git tracks that path. Publisher HTML scan exceptions are limited to
specific reviewed raw paths and require the manifest checksum to match before scanning. This includes
Garrett's public client-side Google Maps token; it never authorizes a server/private credential.
The actual configured private key is independently scanned across every local knowledge artifact,
including raw HTML, refresh decisions, compiled selections and the durable embedding cache.
The literal `n55-ewg-calibration` document slug is excepted only in the two known compiled-corpus
paths, with an AND match on that exact identifier. Source code remains in scan scope.
The MCP SDK is pinned/locked at 2.2.0 for
[CVE-2026-59951](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-84m7-p3x7-pcfv).
The existing HTTP server already uses the unaffected stateless mode and a 64 KiB body limit;
the dependency update removes the known affected SDK version. Focused MCP/knowledge tests and
the Python dependency audit passed; complete exact-head regression remains required.
Source-version revocation invalidates cached candidate selection before reuse. Dedicated SSRF,
parser, injection, poisoning, applicability and spend tests exist. See the completed corrected
implementation evidence in the [Phase 8 acceptance report](../validation/phase-8-acceptance.md).

## Phase 9A feature and dataset boundary

Feature formulas are compiled trusted calculators registered by canonical key; no database text or
operator request is evaluated as Python/SQL. Domain queries bind source values as parameters. The
operator commands accept bounded session IDs, canonical feature keys and aware cutoffs, not raw
SQL or arbitrary formulas. Feature generation caps each batch at 100 pulls and telemetry/history
scans; dataset materialization caps candidate rows, source JSON payload and lineage entities.

Dataset exports can only write into the fixed ignored `apps/api/.artifacts/phase9a/` directory.
Export names are strict filename tokens, parent traversal is rejected, files are atomically
replaced, and JSONL plus manifest are capped at 64 MiB. No dataset export endpoint or new public
API is exposed. The local operator CLI relies on configured database access and OS access to the
workspace; a future network admin surface must add operator authentication/authorization before
exposure. Feature provenance retains source entity IDs in the database, while metric labels and
trace attributes omit them. Missing fuel/sensor data remains null and cannot be supplied by RAG,
stage labels or inferred targets. No model, diagnosis or vehicle-control path is part of this phase.

## Phase 9C offline anomaly detection

The operator CLI refuses the production environment and has no HTTP, MCP, agent or streaming entry
point. Reference and score selection require aware cutoffs and fixed-size bounds; references are
restricted to one vehicle, effective configuration, modification set, source type and role. Feature
values must be Phase 9A versions available by the cutoff. Future, duplicate, invalid, low-quality,
missing required-signal and incompatible-context inputs abstain instead of being treated as normal
or anomalous.

Joblib is trusted code. Phase 9C writes only to the fixed ignored
`apps/api/.artifacts/phase9c/` root, caps artifacts at 50 MiB, writes atomically, and loads only
registry-backed detector versions after checking path, checksum, schema, definition and estimator
allowlist. Caller-supplied paths, pickle payloads and dynamic estimator imports are not accepted.
Reference sets, detector versions, runs and findings are immutable in the database; run-scoped
finding identities prevent overlapping batches from reusing a record owned by another run. The
independent acceptance exercises path traversal, tampering and database immutability. Metrics and
traces omit VINs, vehicle/session/pull IDs, raw telemetry, matrices, checksums and credentials.

## Phase 9D controlled prediction serving

Phase 9D is disabled by default and settings reject enabling it in production. When explicitly
enabled for development/test, a high-entropy operator bearer token is checked in outer ASGI
middleware before request-body parsing or database access. Query, cookie and body credentials are
not accepted. The runtime checks the actual peer address against configured private, loopback or
link-local CIDRs and ignores forwarded headers. This remains operator access to a controlled local
dataset, not user, tenant, or vehicle-owner authorization; public/shared deployment is prohibited.

The serving binding pins one registered 9B/9C version, checksum, task/family, source role,
environment and scope. Approval and lifecycle are append-only; new requests and replays check the
current state. Artifacts load only through the existing trusted registry loaders. Request bodies,
rate, concurrency, body wait, handler duration and CPU workers have explicit bounds. Scoring runs
off the async event loop with fixed numerical thread counts and bounded cancellation handling.

Receipts and events are immutable database records with bounded payload sizes. Responses and
observability omit raw telemetry, VINs, private hashes, full feature matrices, artifact paths and
secrets. The acceptance evaluator tests query/body/cookie credential attempts, forwarded-address
spoofing, public peers, tampered artifacts, unsafe source/context, late inputs, replays, revocation,
receipt mutation and worker/request budgets. Full details are in the
[Phase 9D architecture](../architecture/phase-9d-prediction-service.md) and
[runbook](../runbooks/prediction-service.md).

## Phase 9E prediction evidence

Evidence routes inherit the Phase 9D private-peer, bearer-header, disabled-by-default, production
denial, rate/body/concurrency and timeout controls. The evidence API accepts a receipt ID only; it
cannot accept a new cutoff, raw feature vector, source path or artifact. Reads return a bounded
redacted projection; internal lineage IDs and hashes remain inside controlled persistence. No
vehicle/user ownership or tenant authorization is implied by an operator token.

PostgreSQL rejects updates/deletes across evidence bundles, normalized graph/fact/source rows and
verification audits. A 50 MiB cap and two bounded worker slots protect artifact checksum work; no
untrusted joblib payload is loaded. The trusted application/database can still be privileged and
rewrite all records, so SHA-256 values establish consistency rather than signatures. Metrics and
traces use finite labels and omit vehicle/receipt IDs, VINs, hashes, feature values, paths and
tokens. The disposable evaluator attempts source/artifact tampering, orphan/oversize/duplicate
inserts, partial transaction failure, replay flooding and unauthorized access; it never targets
retained local or production data. See the [Phase 9E architecture](../architecture/phase-9e-prediction-evidence.md)
and [acceptance report](../validation/phase-9e-acceptance.md).
