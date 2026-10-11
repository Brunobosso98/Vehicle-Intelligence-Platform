# Investigation workflow

Phase 7B requires the Phase 7A agent and MCP server. Set a separate
`VIP_AGENT_INVESTIGATION_TOKEN` on the API process. The UI/API caller supplies this token in the
`X-Investigation-Token` header. Keep it server/operator controlled; do not put it in source code,
URLs, logs or checked-in browser configuration. The application has one operator token and does
not provide multi-user vehicle permissions.

1. Ask a vehicle question through the existing agent workspace. Wait for a completed grounded
   AgentRun. An answer with no material missing evidence does not need an investigation.
2. Create an investigation from that run, choosing the actual adapter kind and source reference.
   The service checks existing compatible sessions through MCP before proposing capture.
3. Inspect candidate hypotheses, evidence gaps, unavailable needs, the chosen Phase 4 recipe and
   its hash. If OBD source capability is unknown, set `VIP_AGENT_INVESTIGATION_TOKEN` in the
   collector process and run `vehicle-collector report-capabilities --vehicle-id <id>
--configuration-id <active-id> --source-id <source> --obd-host <host> --gateway <api>`.
   This reads standard Mode 01 support locally and registers an operator-authenticated snapshot.
   A connected collector heartbeat from an earlier matching acquisition is another source. Refresh
   the plan after registration. The report is an operator claim about the local adapter; the
   collector independently checks support again before capture. A technical-documentation gap
   remains a document gap.
4. Approve the exact plan version and recipe hash. A stale version or changed source snapshot must
   be reviewed again. Approval only marks `ACQUISITION_READY`.
5. Start the existing local read-only collector explicitly with the approved Phase 4 recipe. The
   collector rechecks the source and can block unsupported required signals. Follow the normal
   stop/finalize path; canonical telemetry, pulls, events and analytics remain authoritative.
6. Link the finalized DrivingSession by ID. Vehicle, configuration, source, recipe and approval-time
   checks reject an unrelated or old capture. The link creates a separate grounded follow-up run.
7. Inspect the new run and investigation outcome. Statuses can remain inconclusive when required
   evidence is unavailable or quality is insufficient. A new capture cycle requires a new explicit
   plan and approval.

Cancellation stops investigation orchestration; it does not remotely control or stop an external
collector and never deletes canonical data. A failed or interrupted follow-up can be inspected by
its AgentRun ID. An authorized read reconciles a terminal run with the durable investigation.
The API retains bounded replay events; reconnect with the last event sequence. Do not use public
roads or unsafe maneuvers to create a data capture.
