# Phase 6 MCP tool platform

The MCP process is a read-only interface to canonical domain evidence. It calls Phase 0–5 services
directly, never REST or an external model. The shared registry lives in
`apps/api/src/vehicle_platform/mcp/tools.py`; `server.py` registers identifiable resources.
`adapter.py` validates context and translates existing outputs. `catalog.py` selects bounded
vehicle/configuration/session records. Core modules do not depend on MCP.
[ADR 0018](../adr/0018-read-only-mcp-adapter.md) records the boundary and security choices.

[Official SDK](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0) `mcp==2.0.0` is pinned in pyproject/uv.lock. The official `Client` negotiated
`2026-07-28` during acceptance. The server does not pin a revision; older supported clients use
SDK compatibility negotiation. Streamable HTTP and stdio share the same tool/resource inventory.
Legacy SSE is not an exposed transport. There are no prompts or orchestration workflows.

## Tool catalog

| Family    | Tools                                                                                                                         | Bounds/context                                                                                                       |
| --------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Vehicles  | `list_vehicles`, `get_vehicle`, `get_vehicle_configuration`, `list_vehicle_modifications`                                     | Lists 1–100; configuration must belong to vehicle                                                                    |
| Sessions  | `list_sessions`, `get_session`, `get_session_summary`, `get_session_capabilities`                                             | Lists 1–100; explicit vehicle; optional configuration list filter                                                    |
| Pulls     | `list_session_pulls`, `get_pull`, `get_pull_summary`, `compare_pulls`, `get_repeated_pull_analysis`                           | Lists 1–100; comparisons 2–20 unique pulls of one configuration/vehicle                                              |
| Events    | `list_session_events`, `list_pull_events`, `get_event`                                                                        | Lists 1–100; factual evidence and detector identity; no diagnosis                                                    |
| Analytics | `get_session_analytics`, `get_vehicle_baseline`, `get_vehicle_trend`, `compare_configurations`, `get_cross_session_analytics` | 20 selected pulls/500k observations; 2–10 unique sessions; two validated configurations; 2+ pulls per side, 20 total |
| Telemetry | `get_telemetry_window`                                                                                                        | Explicit vehicle/session; 1–8 unique canonical signals; aware positive window ≤60s; 1–1000 ordered samples           |

Tools return structured Pydantic envelopes with schema version 1.0, `data`, `context`, `provenance`,
`returned`, `truncated`, structured `warnings` and `mcp_request_id`. Actual record identifiers and
existing algorithm/configuration hashes remain in data. Units remain canonical. Missing values
remain absent/null; they are never replaced with zero. Warnings include `missing_signal`,
`truncated_result`, `insufficient_history` and existing domain limitation codes.

Analytics uses the existing Phase 5 calculations without persistence. `calculation_id` identifies
a transient versioned snapshot; `analysis_run_id` is null. `source_fingerprint` links selected
canonical inputs. Before/after comparisons report observed associations, never modification causes.
Capability reports use the existing general-health recipe without inserting or updating reports.

## Resources

| Template                              | Meaning                                               |
| ------------------------------------- | ----------------------------------------------------- |
| `vehicle://{vehicle_id}`              | Vehicle context snapshot                              |
| `session://{vehicle_id}/{session_id}` | Session context snapshot with vehicle isolation       |
| `pull://{vehicle_id}/{pull_id}`       | Detected pull snapshot with boundaries and provenance |

Resource content is JSON with the same envelope. These objects may reflect later canonical updates;
they are explicitly snapshots, not immutable URIs. Parameterized calculations remain tools.

## Safety and errors

The allowlist cannot mutate records, run analysis detectors, issue acquisition commands or control
a vehicle. Every database transaction is read-only with statement/lock deadlines. Runtime limits
also enforce eight active calls, ten seconds execution, 64 KiB HTTP input and 512 KiB tool output, counting both compact JSON text and structured content.
List results use a one-extra-record probe and declare truncation; there are no opaque cursors.
Telemetry ordering comes from the existing query service, including sample identity/sequence.

Tool errors use SDK `is_error` and JSON containing only `code` and `mcp_request_id`.
The vocabulary is `INVALID_ARGUMENT`, `NOT_FOUND`, `FORBIDDEN`, `UNAUTHENTICATED`,
`UNSUPPORTED_CAPABILITY`, `INSUFFICIENT_DATA`, `INCOMPATIBLE_CONTEXT`, `RESULT_TOO_LARGE`,
`RATE_LIMITED`, `BACKEND_UNAVAILABLE`, `INTERNAL_ERROR`. Insufficient historical evidence is
normally useful structured output with warnings. SDK HTTP authentication uses 401/403 and its
standard discovery metadata. Untrusted validation values, SQL, paths and exceptions are sanitized.

Progressive disclosure: session summary → pull summary → narrow telemetry window. MCP is not a
bulk exporter. No LLM API key is needed. Phase 7 agent orchestration and Phase 8 diagnosis/retrieval
are outside this phase. See the [runbook](../runbooks/mcp-server.md) and
[acceptance report](../validation/phase-6-acceptance.md).
