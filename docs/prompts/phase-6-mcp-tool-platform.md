You are implementing Phase 6 — MCP Tool Platform for the Vehicle Intelligence Platform.

This is a complete implementation phase.

You are responsible for architecture, implementation, contracts, tests, integration, real protocol E2E, security, observability, documentation, Docker/runtime support, local validation, remote GitHub validation, and final PR creation.

Do not stop after implementing features.

Do not stop after unit tests pass.

Do not stop after local tests pass.

Do not declare Phase 6 complete until:

- the implementation satisfies the Phase 6 scope;
- the independent Phase 6 acceptance suite passes;
- real MCP clients successfully exercise the server;
- the complete local project validation passes;
- changes are committed and pushed;
- a pull request against main exists;
- all required GitHub Actions/checks for the final pushed SHA are green.

DO NOT MERGE THE PULL REQUEST.

The user will manually review and merge it.

======================================================================
BASELINE / PRECONDITIONS
======================================================================

Repository:

Brunobosso98/Vehicle-Intelligence-Platform

Phase 0–5 retrospective hardening has already been merged.

Known Phase 0–5 hardening merge on main:

480e89acdecb6deecd2678389eab3f98fb7f3837

Before doing anything:

git status
git branch --show-current
git remote -v
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git log -5 --oneline

Confirm that the current main contains the Phase 0–5 hardening merge above.

If main has advanced beyond that SHA legitimately, use the current latest main as the Phase 6 baseline, as long as the hardening merge is an ancestor.

Working tree must be clean.

Then create:

codex/phase-6-mcp-tool-platform

Do all Phase 6 work only on this branch.

Do not work directly on main.

Do not force-push.

Do not rewrite existing history.

======================================================================
PHASE 6 PURPOSE
======================================================================

The platform already contains deterministic and validated functionality for:

- vehicles;
- vehicle configurations;
- modifications;
- driving sessions;
- canonical telemetry;
- pulls;
- detected factual events;
- live acquisition;
- deterministic analytics;
- historical baselines;
- trends;
- before/after comparisons;
- configuration-scoped analysis.

Phase 6 must expose these capabilities through a safe, typed, bounded, observable Model Context Protocol layer.

Phase 6 does NOT add an LLM or agent.

The result must be usable by future:

- Phase 7 agent orchestration;
- IDE/desktop MCP hosts;
- external MCP clients;
- automated MCP clients;
- internal platform integrations.

Conceptually:

Vehicle / Sessions / Telemetry
↓
Deterministic domain services
↓
Pull / Event / Analytics engines
↓
MCP Tool + Resource Layer
↓
MCP Client

The MCP layer is an interface over trusted deterministic domain functionality.

It MUST NOT duplicate automotive calculations.

======================================================================
CURRENT MCP BASELINE
======================================================================

Before implementation, verify the current official Model Context Protocol documentation and official Python SDK documentation.

Prefer the current stable official MCP Python SDK compatible with:

Python 3.12.x

At the time Phase 6 was planned, the official Python SDK v2 was the stable line and supported the modern 2026 MCP protocol.

Do not blindly copy v1 examples.

Use official MCP sources.

Prefer the current equivalent of:

MCPServer

rather than deprecated legacy APIs if the installed/current official SDK indicates that.

Production/network transport should use:

Streamable HTTP

Do NOT build new infrastructure around legacy SSE transport.

Also support:

stdio

for local MCP host interoperability and development.

Tests should exercise:

- in-process MCP connection where useful;
- stdio;
- Streamable HTTP.

Do not hard-code a protocol revision unnecessarily.

Allow the official SDK to negotiate protocol versions according to its supported mechanism unless a deterministic compatibility test requires otherwise.

Pin the MCP dependency according to repository dependency-locking conventions.

======================================================================
ARCHITECTURAL RULES
======================================================================

The MCP server must reuse existing domain/application services.

Preferred flow:

MCP tool
→ application/domain service
→ repositories
→ Timescale/Postgres

Avoid:

MCP tool
→ REST API
→ application service

when the MCP server lives in the same codebase and can safely call the application layer directly.

Do not duplicate:

- pull detection;
- event detection;
- canonicalization;
- analytics calculations;
- trend calculations;
- baseline calculations;
- configuration comparison logic.

If an MCP adapter needs a transformation, it may transform domain output into a stable MCP response schema, but business logic remains in the existing service layer.

Maintain clear dependency direction.

MCP-specific modules must not leak MCP protocol objects into core domain modules.

Prefer architecture such as:

domain/application
↑
MCP adapter

not:

domain
→ MCP

======================================================================
SERVER ARCHITECTURE
======================================================================

Inspect the repository and choose the cleanest implementation consistent with existing boundaries.

A reasonable model is:

vehicle_platform/
mcp/
server.py
tools/
resources/
schemas.py
errors.py
auth.py
instrumentation.py

but follow existing repository conventions if a better location already exists.

The same MCP capability set should be usable by:

1. in-process tests;
2. stdio server;
3. Streamable HTTP server.

Avoid maintaining three separate registries.

There should be one canonical MCP server/tool registration implementation.

Provide a documented CLI/runtime entrypoint.

Examples conceptually:

uv run ... mcp --transport stdio

uv run ... mcp --transport streamable-http

Exact commands should follow repository conventions.

======================================================================
PHASE 6 TOOL DESIGN PRINCIPLES
======================================================================

Tools must be:

- read-only;
- deterministic;
- typed;
- bounded;
- explicit;
- composable;
- factual;
- provenance-preserving;
- safe for agent use;
- stable enough for future orchestration.

Do not create giant "do everything" tools.

Do not create:

get_everything
query_database
execute_sql
run_python
shell
fetch_url
send_obd_command
write_ecu
code_module
delete_vehicle
modify_vehicle

Do not expose arbitrary database access.

Do not expose arbitrary file access.

Do not expose arbitrary network access.

Do not expose arbitrary OBD commands.

======================================================================
INITIAL TOOL FAMILIES
======================================================================

Build an intentionally small but complete set of high-value tools.

Exact naming may follow MCP naming conventions, but keep names stable and human-readable.

---

VEHICLE TOOLS
----------------------------------------------------------------------

At minimum support capabilities equivalent to:

list_vehicles

get_vehicle

get_vehicle_configuration

list_vehicle_modifications

Inputs must support bounded selection.

Outputs should expose factual identifiers and context needed by later tools.

---

SESSION TOOLS
----------------------------------------------------------------------

At minimum:

list_sessions

get_session

get_session_summary

get_session_capabilities

Session list must be bounded and support useful filters where existing domain services already support them.

Do not return raw unbounded telemetry.

Session summary should use existing deterministic outputs.

---

PULL TOOLS
----------------------------------------------------------------------

At minimum:

list_session_pulls

get_pull

get_pull_summary

compare_pulls

get_repeated_pull_analysis

Ensure pull comparison obeys Phase 5 comparability rules.

Do not silently compare incompatible vehicle/configuration contexts.

---

EVENT TOOLS
----------------------------------------------------------------------

At minimum:

list_session_events

list_pull_events

get_event

Expose:

- event type;
- severity if defined;
- boundaries;
- factual evidence;
- provenance;
- related pull/session IDs;
- detector/version identity where available.

Do not convert factual events into diagnosis.

---

ANALYTICS TOOLS
----------------------------------------------------------------------

At minimum:

get_session_analytics

get_vehicle_baseline

get_vehicle_trend

compare_configurations

get_cross_session_analytics

Reuse Phase 5 services.

Maintain language/metadata that distinguishes:

observed association

from:

causal conclusion

Never claim that a modification caused an observed difference merely because two configurations differ.

---

TELEMETRY ACCESS
----------------------------------------------------------------------

Do NOT expose a tool that dumps all telemetry.

Provide only bounded access where it is genuinely useful.

If raw/windowed telemetry access is needed for future agents, design something equivalent to:

get_telemetry_window

with mandatory:

- vehicle/session context;
- explicit signal list;
- bounded time window;
- maximum sample count;
- deterministic ordering;
- unit/provenance information.

Also consider a more agent-efficient tool equivalent to:

get_telemetry_window_summary

Prefer summaries/aggregates for routine agent workflows.

Raw samples must always be bounded.

======================================================================
MCP RESOURCES
======================================================================

Expose useful stable MCP resources or resource templates where appropriate.

Examples conceptually:

vehicle://{vehicle_id}

configuration://{configuration_id}

session://{session_id}

pull://{pull_id}

event://{event_id}

analytics://...

Use resource templates if the official current SDK supports them cleanly.

Resources should be:

- immutable or clearly snapshot-like where possible;
- machine-readable;
- schema-versioned;
- provenance-rich.

Avoid duplicating every tool as a resource without purpose.

Tools are for parameterized operations.

Resources are for identifiable context objects.

======================================================================
PROMPTS
======================================================================

Do not build Phase 7 behavior in Phase 6.

MCP prompt templates are optional.

Only add MCP prompts if they clearly improve protocol completeness without introducing reasoning/orchestration semantics.

Do NOT add:

- diagnostic agent prompts;
- autonomous workflows;
- planning prompts;
- multi-agent behavior.

Phase 6 is primarily the tool/resource platform.

======================================================================
STRUCTURED OUTPUT
======================================================================

Every meaningful MCP tool must return structured machine-readable content.

Prefer typed Pydantic/domain-compatible schemas.

Do not return only prose.

Each response should contain the minimum applicable metadata such as:

schema_version

vehicle_id

configuration_id

session_id

pull_id

event_id

analysis_run_id

algorithm_version

calculation_version

source

provenance

observed_at / calculated_at where applicable

units

result counts

truncation information

pagination/cursor information where applicable

Do not fabricate unavailable values.

Represent unavailable capabilities explicitly.

======================================================================
COMMON MCP RESPONSE ENVELOPE
======================================================================

Design a consistent response model.

The exact schema may differ by tool, but responses should consistently communicate:

data

provenance

context

schema_version

truncated

warnings

or equivalent.

Do not hide warnings inside free-form strings.

Examples of warnings:

insufficient_history

missing_signal

configuration_mismatch

capability_unavailable

partial_window

truncated_result

======================================================================
ERROR MODEL
======================================================================

Design deterministic MCP-visible errors.

At minimum distinguish cases equivalent to:

INVALID_ARGUMENT

NOT_FOUND

FORBIDDEN

UNAUTHENTICATED

UNSUPPORTED_CAPABILITY

INSUFFICIENT_DATA

INCOMPATIBLE_CONTEXT

RESULT_TOO_LARGE

RATE_LIMITED

BACKEND_UNAVAILABLE

INTERNAL_ERROR

Use the MCP protocol/SDK's standard error mechanisms where appropriate.

Do not leak:

- SQL;
- stack traces;
- filesystem paths;
- credentials;
- bearer tokens;
- internal infrastructure details.

Preserve server-side diagnostic correlation IDs.

======================================================================
BOUNDS / RESOURCE SAFETY
======================================================================

Every tool must have explicit bounds.

Review each operation for:

- max list length;
- max date range;
- max sessions;
- max pulls;
- max events;
- max telemetry samples;
- max signals;
- max comparison objects;
- max payload size;
- query timeout;
- execution timeout.

Do not rely only on UI limits.

Enforce limits server-side.

Never allow an MCP client to accidentally request millions of telemetry rows.

Prefer pagination/cursors where appropriate.

If pagination is implemented, test cursor misuse and invalid cursors.

======================================================================
READ-ONLY SAFETY MODEL
======================================================================

Phase 6 is strictly read-only.

MCP must not expose tools that:

- mutate vehicle data;
- mutate configuration;
- delete data;
- change analysis results;
- create live acquisition commands;
- send OBD commands;
- write ECU parameters;
- flash software;
- code vehicle modules;
- trigger vehicle actuation.

Even if the underlying REST API currently supports some mutation, MCP Phase 6 should expose only approved read-only behavior.

Document this boundary explicitly.

======================================================================
AUTHENTICATION / AUTHORIZATION
======================================================================

stdio:

Treat as a local process transport.

Do not invent network authentication inside stdio.

Still enforce the same tool-level read-only allowlist and resource bounds.

Streamable HTTP:

Must not be an unauthenticated wide-open production endpoint.

Use the current official MCP SDK authorization capabilities or integrate cleanly with existing application authentication infrastructure.

Avoid implementing an authorization server from scratch unless the repository already has one.

A reasonable design may provide:

- local development loopback mode;
- bearer/token verifier;
- MCP read scope or equivalent;
- production-safe configuration.

Use the official current MCP authorization model where applicable.

Do not weaken current application security.

Do not expose secrets in discovery metadata or logs.

Test:

- valid token;
- missing token;
- invalid token;
- expired token if supported;
- insufficient scope;
- token redaction.

======================================================================
NETWORK SAFETY
======================================================================

Default network binding should be safe.

Prefer loopback by default.

Do not silently bind MCP to 0.0.0.0 in developer mode unless Docker/runtime configuration explicitly requires it.

Container binding and host exposure should follow existing project conventions.

If a container requires 0.0.0.0 internally, control external exposure via Compose/network configuration.

======================================================================
TOOL DISCOVERY
======================================================================

A real MCP client must be able to discover the tool inventory.

Test:

list_tools

Validate:

- expected tool names;
- descriptions;
- argument schemas;
- output schemas where exposed by SDK;
- annotations/capabilities supported by the current protocol.

Descriptions should help future LLMs select the correct tool.

Descriptions must clearly state:

- what the tool returns;
- what it does not infer;
- relevant bounds;
- context/comparability constraints.

Avoid vague descriptions.

======================================================================
RESOURCE DISCOVERY
======================================================================

Where MCP resources are implemented, verify with a real MCP client:

list_resources

and/or:

list_resource_templates

Then read selected resources.

Test invalid resource IDs.

======================================================================
PROVENANCE REQUIREMENTS
======================================================================

A future agent must be able to trace a claim back to platform evidence.

For example:

agent statement
→ compare_pulls
→ analytics run
→ pull IDs
→ session IDs
→ configuration ID
→ telemetry provenance

The MCP layer must retain enough identifiers for this chain.

Do not flatten results into anonymous values.

======================================================================
MCP CALL IDENTITY
======================================================================

Introduce or preserve an execution identity for each MCP call.

Where practical record:

mcp_request_id

tool_name

transport

caller/client identity if available

start/end

duration

success/failure

result cardinality

truncated flag

correlation/trace ID

Do not log raw sensitive payloads unnecessarily.

======================================================================
OBSERVABILITY
======================================================================

Add Phase 6 observability integrated with existing OpenTelemetry/metrics architecture.

Metrics should include useful equivalents to:

mcp_tool_calls_total

mcp_tool_errors_total

mcp_tool_duration_seconds

mcp_active_calls

mcp_result_items

mcp_truncated_results_total

mcp_auth_failures_total

Do not create unbounded metric labels.

Never use arbitrary vehicle IDs/session IDs/tool arguments as high-cardinality labels.

Tracing:

A tool call should produce spans that can connect:

MCP request
→ MCP tool
→ domain service
→ database/query

Where existing domain spans already exist, preserve trace context.

Test delivered spans, not merely instrumentation configuration.

Ensure SQL/token redaction continues to work.

======================================================================
LOGGING
======================================================================

Use structured logging consistent with the existing application.

Include:

request/tool correlation

tool name

status

duration

bounded result metadata

Do NOT log:

raw bearer tokens

entire telemetry payloads

full uploaded files

sensitive SQL

unbounded tool arguments

======================================================================
DOCKER / COMPOSE
======================================================================

Make MCP runnable using the repository's container workflow.

Prefer a dedicated MCP process/service reusing the backend application image or shared source layers when architecturally appropriate.

Do not unnecessarily duplicate a massive image.

Compose should support a real Streamable HTTP MCP endpoint.

Add health/readiness behavior if appropriate.

MCP container/process readiness must verify more than "TCP port open".

Use protocol-level or application-level readiness where feasible.

Do not break existing Phase 0–5 services.

======================================================================
STDIO SUPPORT
======================================================================

Provide an officially supported stdio entrypoint.

A real official MCP Python client test must launch the server as a subprocess and:

- connect;
- discover tools;
- call representative tools;
- disconnect cleanly.

The child process must not emit protocol-corrupting output to stdout.

Logs for stdio mode should go to stderr or configured structured destinations as appropriate.

Test this explicitly.

======================================================================
STREAMABLE HTTP SUPPORT
======================================================================

Provide production-oriented Streamable HTTP.

Do not use legacy SSE as the primary Phase 6 HTTP transport.

A real official MCP client must connect to the actual running endpoint.

Exercise:

connect/discovery

list tools

tool call

resource read where implemented

authentication

invalid request

connection lifecycle

concurrent calls

server shutdown/restart behavior

======================================================================
REPRESENTATIVE TOOL E2E FLOW
======================================================================

Build deterministic Phase 6 test fixtures using existing real stack services.

The E2E must not rely on arbitrary developer history in the database.

Create controlled:

vehicle

configurations

sessions

telemetry

pulls

events

analytics history

Then use a real MCP client to perform a flow conceptually similar to:

list_vehicles
→ select fixture vehicle

list_sessions(vehicle)
→ select known session

get_session_summary(session)

list_session_pulls(session)

get_pull_summary(pull)

list_pull_events(pull)

compare_pulls([...])

get_vehicle_baseline(vehicle, configuration)

get_vehicle_trend(vehicle, signal/metric)

compare_configurations(before, after)

Assertions must validate actual values and identifiers.

Do not merely assert that results are non-empty.

======================================================================
INDEPENDENT PHASE 6 ACCEPTANCE SUITE
======================================================================

Create:

make phase6-acceptance

or equivalent consistent with the repository.

It must NOT simply alias unit tests.

Create an independent acceptance evaluator such as:

scripts/evaluate_mcp.py

or appropriate repository convention.

The evaluator must use an actual MCP client.

Acceptance should verify:

- server capability discovery;
- expected tool inventory;
- input schemas;
- structured results;
- deterministic fixture values;
- provenance;
- context propagation;
- bounds;
- errors;
- read-only guarantees;
- unsupported cases;
- configuration isolation;
- comparability enforcement.

Include both successful and negative scenarios.

At minimum test:

valid vehicle lookup

unknown vehicle

bounded session list

session summary

valid pull summary

invalid pull

pull comparison same configuration

incompatible comparison

event lookup

baseline with sufficient history

baseline insufficient history

configuration comparison

bounded telemetry request

oversized telemetry request

missing capability

invalid arguments

authentication failure for HTTP

======================================================================
PROTOCOL E2E TESTS
======================================================================

Create true protocol E2E coverage.

At minimum three levels:

---

1. IN-PROCESS MCP

---

Use official client/server in-process transport if supported.

Purpose:

fast protocol-level contract testing.

Verify:

discovery

tool schemas

tool calls

resources

errors

---

2. STDIO E2E

---

Launch the actual MCP server subprocess.

Connect using official MCP client stdio transport.

Verify:

process startup

protocol negotiation

list_tools

representative calls

structured output

clean shutdown

stderr/stdout correctness

---

3. STREAMABLE HTTP E2E

---

Run the real Docker/Compose stack.

Connect using official MCP client over Streamable HTTP.

Verify:

protocol negotiation

authentication

discovery

representative tools

resources

errors

concurrency

reconnect after MCP service restart

Do not mock the MCP transport for this test.

======================================================================
CONCURRENCY / RESILIENCE
======================================================================

Test safe concurrent read calls.

For example:

multiple session summaries

multiple pull lookups

parallel analytics calls

Do not allow resource exhaustion.

Test at least one controlled MCP server restart:

client call
→ server unavailable/restarting
→ service returns
→ new client reconnects
→ deterministic result remains correct

No data mutation should occur.

Test backend dependency failure:

MCP
→ domain service
→ database unavailable

Expected:

bounded failure

sanitized error

observable failure

successful recovery after DB returns

Do not convert dependency failure into generic hanging until timeout.

======================================================================
CANCELLATION / TIMEOUTS
======================================================================

Where supported by the official SDK/protocol, ensure client cancellation does not leave runaway database/domain work.

Apply bounded execution time.

Test a deterministic timeout path where practical.

Do not fake slow sleeps solely to pass a timeout test if a more realistic bounded query path exists.

======================================================================
TOOL ANNOTATIONS
======================================================================

If the current MCP specification/SDK supports tool behavior annotations, use correct read-only/idempotent semantics where appropriate.

Do not invent unsupported annotation fields.

Verify against official MCP documentation before implementation.

======================================================================
SCHEMA VERSIONING
======================================================================

Define Phase 6 MCP schema version strategy.

The MCP protocol version and application tool output schema version are separate concepts.

Do not confuse them.

Example conceptual application schema:

vehicle-platform.mcp/v1

or equivalent.

Document compatibility expectations.

Do not prematurely create a complicated version-negotiation framework.

======================================================================
TOOL REGISTRY
======================================================================

Maintain one source of truth for the tool catalog.

Avoid scattering duplicate metadata between:

server registration

docs

tests

frontend

Prefer generation or assertions where appropriate.

Acceptance should detect accidental tool removal or unexpected mutation tool exposure.

======================================================================
SECURITY REVIEW
======================================================================

Perform an explicit Phase 6 threat review.

Update:

docs/security/threat-model.md

or equivalent.

Review at minimum:

unauthorized MCP HTTP access

token leakage

scope escalation

arbitrary tool execution

tool argument injection

SQL injection

resource enumeration

cross-vehicle data leakage

cross-configuration data leakage

oversized requests

unbounded telemetry extraction

denial of service via expensive analytics

high-cardinality observability abuse

error leakage

stdio protocol corruption

container/network exposure

The read-only design is mandatory but not sufficient.

======================================================================
CROSS-VEHICLE ISOLATION
======================================================================

Explicitly test that identifiers from different vehicles cannot be improperly combined.

Examples:

vehicle A + session B

pull A + vehicle B

configuration A + vehicle B

comparison across disallowed vehicle contexts

Return deterministic errors.

Never silently substitute context.

======================================================================
CONFIGURATION ISOLATION
======================================================================

Preserve Phase 5 configuration semantics.

Tools must not accidentally mix:

configuration A

configuration B

unless the requested operation explicitly performs a validated before/after/configuration comparison.

Test this through MCP, not only through domain unit tests.

======================================================================
MISSING CAPABILITY BEHAVIOR
======================================================================

A vehicle/session may not contain:

boost

HPFP

IAT

or another signal.

MCP must expose this accurately.

Do not return 0 when a signal is unavailable.

Use explicit capability/unavailable semantics.

======================================================================
RAW DATA POLICY
======================================================================

Do not use MCP as a bulk telemetry export mechanism.

Set sensible upper bounds.

If a future agent genuinely needs deeper telemetry, it should progressively request narrow windows.

Document expected progressive-disclosure workflow such as:

session_summary
→ pull_summary
→ telemetry_window

not:

all_telemetry

======================================================================
NO LLM IN PHASE 6
======================================================================

Do NOT add:

OpenAI calls

Anthropic calls

LangGraph

agent loops

planner

reasoning engine

embeddings

vector database

RAG

conversation memory

prompt chaining

Phase 6 must pass 100% without any LLM API key.

======================================================================
NO NEW FRONTEND REDESIGN
======================================================================

Do not redesign the existing frontend in this phase.

The current frontend will receive a dedicated UX/product hardening phase later.

Only modify frontend code if Phase 6 requires a minimal integration/status surface and if that adds meaningful validation value.

Prefer protocol E2E over adding a decorative MCP page.

Do not break existing Playwright selectors unnecessarily.

======================================================================
DOCUMENTATION
======================================================================

Create/update appropriate documents.

At minimum:

docs/architecture/phase-6-mcp-tool-platform.md

docs/runbooks/mcp-server.md

docs/validation/phase-6-acceptance.md

Update:

README

component architecture

service boundaries

testing strategy

observability documentation

security threat model

Add an ADR if an architectural decision warrants it.

Document:

architecture

transports

tool catalog

resource catalog

authentication

bounds

errors

provenance

observability

local usage

Docker usage

stdio usage

Streamable HTTP usage

testing

known limitations

future Phase 7 integration boundary

======================================================================
PHASE 6 TRACEABILITY LEDGER
======================================================================

Create:

docs/validation/phase-6-traceability-ledger.md

For every Phase 6 requirement record:

Requirement ID

Requirement

Architecture evidence

Implementation evidence

Test evidence

Integration evidence

Protocol E2E evidence

Security evidence

Observability evidence

Status

Only mark VERIFIED when supported by real evidence.

======================================================================
TEST COVERAGE
======================================================================

Maintain or improve existing coverage thresholds.

Do not weaken:

API coverage

frontend coverage

branch coverage

typing

lint

formatting

security

Existing Phase 0–5 tests must remain green.

Add focused unit tests for:

tool schemas

tool adapters

resource adapters

error mapping

bounds

auth

provenance

instrumentation

======================================================================
DATABASE INTEGRATION
======================================================================

If Phase 6 does not require a new database schema, do not create a migration merely to mark the phase.

Prefer no new tables unless there is a genuine need.

If persistent MCP execution audit records are justified, critically evaluate whether existing logs/traces provide sufficient evidence first.

Do not persist every MCP call merely for convenience.

If a migration is introduced:

test clean upgrade

direct parent downgrade

re-upgrade

earlier-phase preservation

Timescale integrity

======================================================================
PERFORMANCE
======================================================================

Add a meaningful MCP benchmark.

Do not benchmark a no-op tool.

Measure representative read tools.

For example:

session summary

pull summary

vehicle baseline

concurrent lightweight calls

Record:

request count

success/error count

latency p50

latency p95

latency p99 where meaningful

throughput

memory behavior

result sizes

Do not create unrealistic performance claims.

The objective is bounded predictable behavior, not arbitrary high RPS.

======================================================================
MCP RESULT SIZE TESTS
======================================================================

Measure/verify upper bounds.

Test a large legitimate dataset.

Ensure:

response remains bounded

truncated indicator is correct

pagination/window limits work

memory remains bounded

Do not silently truncate without reporting it.

======================================================================
PHASE 6 MAKE TARGETS
======================================================================

Add repository-conventional commands.

Expected conceptual commands:

make phase6-acceptance

make test-mcp

make test-mcp-e2e

make benchmark-mcp

Names may vary if repository conventions suggest better names.

Integrate Phase 6 acceptance into the appropriate full verification gate.

Do not make the full gate impractically redundant, but all required correctness must be covered.

======================================================================
PHASE 0–5 REGRESSION REQUIREMENT
======================================================================

Phase 6 must not regress previous phases.

Run the existing:

Phase 0 validation

Phase 1 acceptance

Phase 2 acceptance

Phase 3 acceptance

Phase 4 acceptance

Phase 5 acceptance

Phases 0–5 aggregate acceptance

and all current full project gates.

If an existing test fails because of Phase 6, investigate the regression.

Do not simply update the expectation unless behavior intentionally and correctly changed.

======================================================================
LOCAL IMPLEMENTATION LOOP
======================================================================

Work autonomously.

Use this loop:

inspect
→ design
→ implement small slice
→ focused unit tests
→ integration tests
→ MCP acceptance
→ protocol E2E
→ security/observability
→ full validation
→ review

Do not wait until the end to run tests.

If something fails:

diagnose root cause

fix

rerun focused test

rerun broader gate

Continue until green.

======================================================================
LOCAL FINAL VALIDATION
======================================================================

Before push, run all applicable repository validation.

At minimum include current equivalents of:

make bootstrap

make check-api

make check-web

make contracts-check

make docs-check

make phase1-acceptance

make phase2-acceptance

make phase3-acceptance

make phase4-acceptance

make phase5-acceptance

make phases-0-5-acceptance

make phase6-acceptance

make test-integration

make test-mcp

make test-mcp-e2e

make build

make containers

make up

make test-e2e

make stack-check

make security

make observability-full

make benchmark-mcp

make live-stream-benchmark

make verify

Use actual repository command names if they differ.

Do not skip failures.

======================================================================
CLEAN-STATE REVALIDATION
======================================================================

After the first complete green run:

use project-supported cleanup mechanisms;

discard only disposable test state;

preserve user data;

rebuild/restart necessary services;

rerun critical Phase 6 acceptance from a clean state.

At minimum rerun:

container build

database integration

MCP protocol E2E

Phase 6 acceptance

security

observability

full verify

This must prove that the success was not caused by:

stale containers

previous fixture data

cached state

previous MCP process

old database state

======================================================================
CODE REVIEW BEFORE COMMIT
======================================================================

Inspect:

git status

git diff --stat

git diff

Review every changed file.

Remove:

debug prints

temporary logs

sleep-based test hacks

giant timeout workarounds

unused code

commented experiments

local absolute paths

secrets

Zone.Identifier

Playwright caches

test artifacts

generated temporary reports not intended for Git

Do not weaken existing assertions.

======================================================================
COMMITS
======================================================================

Create logical commits.

Example grouping:

feat: add MCP tool and resource platform

feat: add MCP transports and authorization

test: add MCP acceptance and protocol e2e

chore: integrate MCP runtime and observability

docs: document phase 6 MCP platform

Actual grouping should reflect actual changes.

Do not create meaningless micro-commits.

======================================================================
FINAL COMMITTED-HEAD VALIDATION
======================================================================

After all code is committed:

git status

must be clean.

Record:

git rev-parse HEAD

Run the critical validation against that exact committed HEAD.

If any fix is made afterward:

commit the fix

obtain new HEAD

rerun validation

The validated SHA must be the final pushed SHA.

======================================================================
PUSH
======================================================================

Push:

git push -u origin codex/phase-6-mcp-tool-platform

Do not force-push.

======================================================================
PULL REQUEST
======================================================================

Create a PR against:

main

Suggested title:

feat: add Phase 6 MCP tool platform

PR body must include:

Phase 6 objective

architecture

MCP SDK/protocol baseline

tool catalog

resource catalog

stdio support

Streamable HTTP support

authentication/security

bounds

provenance

observability

tests

protocol E2E

benchmark

Phase 0–5 regression results

Phase 6 acceptance result

final validated local SHA

known limitations

explicit note:

NO LLM / AGENT / RAG functionality was added.

Do NOT merge the PR.

======================================================================
REMOTE GITHUB VALIDATION
======================================================================

The job is NOT complete when the PR is opened.

Use GitHub CLI to monitor the PR.

Examples conceptually:

gh pr view

gh pr checks --watch

gh run list

gh run view <run>

Use actual commands supported by installed gh.

Wait for required checks for the final pushed SHA.

Expected important workflows currently include equivalents of:

CI

Security

Phase 0 full validation / canonical Docker full-stack gate

plus any new Phase 6 workflow added.

If ANY required GitHub check fails:

inspect the failing job/log

determine root cause

fix locally

run focused validation

run relevant broader validation

commit

push

wait for new GitHub checks

Repeat until all required checks for the FINAL HEAD are green.

Do not stop after reporting:

"GitHub test failed."

Fix it.

Do not declare success if:

a workflow is pending

a workflow was cancelled

a required job was skipped unexpectedly

a check belongs to an older SHA

Validate that the checks correspond to the final PR HEAD.

======================================================================
DO NOT MERGE
======================================================================

Even after every GitHub check passes:

DO NOT merge the pull request.

Leave the PR open and mergeable.

The user will manually review and merge it.

======================================================================
PHASE 6 DEFINITION OF DONE
======================================================================

Phase 6 is complete only when ALL are true:

Architecture

[ ] MCP is a clean adapter over Phase 0–5 domain services
[ ] no automotive calculation duplication
[ ] no LLM/agent/RAG scope introduced

Protocol

[ ] official current MCP SDK
[ ] tool discovery works
[ ] structured tool calls work
[ ] resources work where implemented
[ ] stdio works
[ ] Streamable HTTP works
[ ] legacy SSE is not the primary transport

Tools

[ ] vehicle tools
[ ] session tools
[ ] pull tools
[ ] event tools
[ ] analytics tools
[ ] bounded telemetry access if implemented

Safety

[ ] read-only tool set
[ ] no arbitrary SQL
[ ] no arbitrary shell
[ ] no arbitrary OBD
[ ] no ECU write/control
[ ] server-side bounds
[ ] cross-vehicle isolation
[ ] configuration isolation

Security

[ ] HTTP authentication
[ ] authorization/scope behavior
[ ] token redaction
[ ] safe network binding
[ ] request/result limits
[ ] threat model updated

Provenance

[ ] vehicle/config/session/pull/event IDs retained
[ ] algorithm/calculation identity retained
[ ] source provenance retained

Observability

[ ] MCP logs
[ ] metrics
[ ] spans
[ ] DB/domain trace continuity
[ ] error tracing
[ ] no high-cardinality label abuse

Testing

[ ] unit
[ ] integration
[ ] independent Phase 6 acceptance
[ ] in-process MCP
[ ] stdio real-client E2E
[ ] Streamable HTTP real-client E2E
[ ] auth negative tests
[ ] bounds negative tests
[ ] backend failure/recovery
[ ] MCP restart/reconnect
[ ] Phase 0–5 regression tests

Performance

[ ] meaningful MCP benchmark
[ ] bounded result sizes
[ ] bounded memory
[ ] latency recorded

Documentation

[ ] Phase 6 architecture
[ ] tool catalog
[ ] resource catalog
[ ] runbook
[ ] threat model
[ ] validation report
[ ] traceability ledger

Delivery

[ ] working tree clean
[ ] final committed HEAD validated
[ ] branch pushed
[ ] PR opened against main
[ ] final remote CI green
[ ] final remote Security green
[ ] final canonical/full-stack gate green
[ ] Phase 6 remote checks green if introduced
[ ] PR NOT merged

======================================================================
FINAL PHASE 6 REPORT
======================================================================

When everything is done, return one final report containing:

1. Branch
2. Base main SHA
3. Final Phase 6 HEAD SHA
4. PR number and URL
5. PR state
6. Git status
7. Architecture implemented
8. MCP SDK/version used
9. Negotiated protocol version observed in tests
10. Tool inventory
11. Resource inventory
12. stdio result
13. Streamable HTTP result
14. Authentication result
15. Bounds/resource safety result
16. Cross-vehicle/configuration isolation result
17. Provenance result
18. Observability result
19. Unit tests
20. Integration tests
21. MCP protocol E2E tests
22. Phase 6 acceptance result
23. Existing Phase 0–5 regression result
24. Performance benchmark
25. Security result
26. Full local verify result
27. Clean-state revalidation result
28. GitHub CI result for final SHA
29. GitHub Security result for final SHA
30. GitHub canonical/full-stack result for final SHA
31. Other required remote checks
32. Known limitations
33. Explicit deferred Phase 7/8 functionality
34. Confirmation that PR was NOT merged

End with exactly:

PHASE 6 — MCP TOOL PLATFORM: VERIFIED

only if every required local and remote acceptance condition above is satisfied.

Otherwise end with:

PHASE 6 — MCP TOOL PLATFORM: NOT VERIFIED

and continue working if the failure is within your ability to fix.

Do not claim VERIFIED merely because implementation exists.

Do not claim VERIFIED merely because unit tests pass.

Do not claim VERIFIED merely because local tests pass.

The final PR HEAD must be the exact SHA validated locally and remotely.

Do not merge the PR.
