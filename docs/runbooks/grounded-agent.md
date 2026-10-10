# Grounded agent operation

A completed answer with a material evidence gap can start a separate Phase 7B investigation.
The [investigation runbook](investigation-workflow.md) covers source preflight, recipe review,
explicit approval, compatible session linking and follow-up recovery.

The agent is disabled by default. Apply migrations through `make db-migrate` and run the existing
MCP server before enabling agent execution. No vehicle control or ECU writes are available.

## Local configuration

Use environment variables:

| Variable                    | Purpose                                                   |
| --------------------------- | --------------------------------------------------------- |
| `VIP_AGENT_ENABLED=true`    | Enable agent admission                                    |
| `VIP_AGENT_PROVIDER=openai` | Real provider; the default                                |
| `VIP_AGENT_MODEL`           | Explicit Responses-capable model selected by the operator |
| `VIP_AGENT_API_KEY`         | Provider credential, never a browser variable             |
| `VIP_AGENT_MCP_URL`         | Fixed operator MCP URL; localhost HTTP or HTTPS           |
| `VIP_AGENT_MCP_TOKEN`       | MCP bearer token matching `VIP_MCP_TOKEN`                 |

For Docker, `compose.yaml` forwards the agent settings to the API and uses `http://mcp:8001/mcp`.
`make mcp-up` starts the authenticated MCP profile. The operator must provide the same token to
the API and MCP processes. Never commit keys or put them in a question, URL or shell argument.
The Compose MCP profile explicitly enables `VIP_MCP_ALLOW_DOCKER_INTERNAL_HOST=true` to allow
the exact internal authority `mcp:8001`. Standalone MCP defaults to rejecting that authority;
DNS rebinding protection and the configured Origin policy remain enabled.
For reproducible development/CI only, `VIP_AGENT_PROVIDER=deterministic` works in test/development
mode. Enabling deterministic mode in production fails startup.

Question API: POST `/api/v1/vehicles/{id}/agent-runs` with `question`, optional `session_id` and
optional `previous_run_id`. Retrieve the run, `/audit`, `/events`, `/stream?after=N`, or POST `/cancel`.
History is bounded by `limit=1..20`. A follow-up must reference a completed run of the same vehicle;
it transfers only a bounded previous question and reads evidence again.
Question bodies are limited to 32 KiB and five seconds before JSON decoding. Per process,
admission permits 20 new questions per minute with a burst of 20; other agent requests share
a burst of 200 and refill at 100/second. At most 64 requests and four executions are active.
These are local resource limits, not user account quotas. Oversized, slow or rate limited requests
return sanitized 413, 408 or 429 errors.
The 90-second execution deadline also covers publishing validated answer chunks. Terminal
persistence and provider cleanup have separate bounded five-second and two-second deadlines.

The application currently has no end-user authentication or tenant authorization. Keep it inside the
existing trusted local/operator boundary. MCP bearer authentication protects the tool transport; it
does not add end-user authorization to the public application API.

## Validation commands

| Command                    | Proof                                                               |
| -------------------------- | ------------------------------------------------------------------- |
| `make test-agent`          | Unit provider/state/policy/grounding/lifecycle branches             |
| `make test-integration`    | Disposable migration, persistence and existing phase regressions    |
| `make phase7a-acceptance`  | Independent golden stdio suite and actual HTTP recovery             |
| `make test-agent-e2e`      | Built Next.js app, real HTTP API/MCP, browser evidence flow         |
| `make benchmark-agent`     | Deterministic latency/resource measurements, concurrency and bounds |
| `make agent-observability` | Disposable container trace/metric delivery and secret redaction     |
| `make agent-real-smoke`    | Optional billable real-provider controlled-fixture smoke            |
| `make verify`              | Canonical full local validation, including Phase 7A                 |

These commands create disposable `vehicle_test` databases. Their cleanup is limited to the project
they created. They never reset retained vehicle-platform volumes. Evidence lives in `.validation/agent`;
the canonical GitHub gate uploads it with the checked commit SHA. Ordinary CI requires no LLM key.

Real smoke needs both provider key and model in the environment and may incur provider charges.
Deterministic CI proves orchestration, bounds, transport, structural grounding and public rendering.
It does not prove real-model question interpretation, model availability, model latency or billing.

## Failure handling

Check public `error_category`, tool audit, trace ID and sanitized operational logs. Do not enable
logging of prompts, SDK bodies, SQL parameters or provider reasoning. Invalid configuration fails
closed. Provider authentication errors are terminal; only availability/rate failures receive bounded
retries. Invalid claims get one correction by default. No failed run returns an unverified answer.

After a stream disconnect, retrieve the run or reconnect using the last sequence. Cancellation is
explicit; browser disconnection does not cancel the run. After a process restart or database outage,
retrieval classifies old running records as `execution_interrupted` after the bounded recovery window.
Start a new run after dependencies recover. Never replay a graph or copy previous evidence IDs into it.
After a database interruption, retry a new question once connectivity recovers. The HTTP gate pauses
its disposable database without discarding the fixture, verifies a bounded safe 503, then unpauses
it and requires successful new execution. An owned driver watchdog bounds cancellation cleanup.
