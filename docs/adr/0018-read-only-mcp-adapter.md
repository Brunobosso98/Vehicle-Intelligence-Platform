# ADR 0018: Read-only MCP application adapter

## Status

Accepted. Extends [ADR 0016](0016-deterministic-versioned-automotive-analytics.md).

## Context

Phase 6 needs typed tools for existing evidence, through both local hosts and network clients.
The existing analytics and capability services persist their results even when called as reads.
Exposing those methods unchanged would violate the MCP read-only boundary.
The official Python SDK stable release is 2.0.0, with `MCPServer` and negotiated protocol eras.

## Decision

Use one official `MCPServer` registration for in-process, stdio and Streamable HTTP clients.
Pin and lock SDK 2.0.0. Keep MCP imports inside the adapter; call application services directly.
Add explicit nonpersistent analytics/capability options using the existing calculations.
A transient calculation has a deterministic UUID derived from its version, configuration and
source fingerprint. It is returned as `calculation_id`; `analysis_run_id` is null. It never
claims to be a stored run. Existing REST persistence behavior and schema revisions remain intact.

All MCP transactions are read-only, with 5s statement and 1s lock deadlines. Each call has a
10s execution deadline and the process admits eight simultaneous calls. Expose only the approved
22 read tools and three contextual resource templates. No SQL/shell/network/hardware passthrough.

HTTP uses SDK bearer verification and the `mcp:read` scope, with an operator-provisioned opaque
token, optional expiry, constant-time comparison, protected resource metadata and explicit binding.
The server is a resource server; it does not mint tokens or implement an authorization server.
Local HTTP defaults to loopback; Compose binds internally to all interfaces but publishes loopback.
Production public resource/issuer URLs require HTTPS. Operators terminate TLS and provision
appropriate database credentials. A provisioned reader can read all repository vehicles; there
is no tenant model. Stdio trusts its process owner and uses no network authentication.

Responses are versioned snapshots with structured warnings, source context and correlation IDs.
Enforce limits in both input schemas and execution, including a 512 KiB serialized tool result.
SDK text and structured representations are both counted. Oversized results fail explicitly.
Metrics have a closed tool/error vocabulary; entity IDs belong only in provenance and traces.
No new database migration or persistent audit table is justified; logs/metrics/traces provide audit.

## Alternatives

REST forwarding would introduce a network hop and blur process authentication. A second MCP
implementation or three registries would duplicate contracts. Copying automotive algorithms into
MCP would permit drift. Persisting analytics from tools would violate read-only operation.
A new OAuth authorization server is unnecessary for this operator-controlled platform.

## Consequences and risks

Reads may perform bounded deterministic calculations and are more expensive than record lookups.
History selectors retain Phase 5 limits; completeness and selection metadata must remain explicit.
The token is a deployment capability, not tenant authorization. External hosts may supply it as a
bearer credential; automated OAuth token issuance remains a future integration decision.
Future agents consume this evidence interface but reasoning, diagnosis, LLMs and RAG remain deferred.
