# Initial threat model

Phase 0 is a localhost engineering stack, without accounts or vehicle commands. It is not an
Internet deployment. DB credentials in .env.example are public local examples, never production credentials.

| Threat                               | Status              | Mitigation / next boundary                                                        |
| ------------------------------------ | ------------------- | --------------------------------------------------------------------------------- |
| Secret leakage                       | mitigated           | gitignore, redacted scans, no credentials in logs/errors/client bundles           |
| Dependency compromise / supply chain | partially mitigated | locks, release age, Dependabot, audits/scans; future signed provenance            |
| Injection                            | partially mitigated | no user SQL/file ingestion; parameterized SQL boundary; Phase 1 parser validation |
| Broken authorization                 | future phase        | authentication/authorization before public deployment or personal vehicle records |
| Malicious log/file input             | future phase        | size limits, strict parsers, sandboxing and fuzzing before ingestion              |
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
