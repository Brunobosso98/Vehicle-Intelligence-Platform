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
