"""Independent acceptance oracle: closed permissions, public counters and exact citations."""

COMMON = {"get_session_summary", "list_session_pulls", "get_pull_summary"}
HISTORY = {"get_vehicle_baseline", "get_vehicle_trend", "get_cross_session_analytics"}
EVENTS = {"list_session_events", "get_event"}
PERMISSIONS = {
    "data_quality": {"get_session", "get_session_capabilities", "get_session_summary"}
    | EVENTS,
    "performance": COMMON
    | HISTORY
    | {
        "list_sessions",
        "get_session",
        "get_pull",
        "compare_pulls",
        "get_repeated_pull_analysis",
        "compare_configurations",
    },
    "thermal": COMMON | HISTORY | EVENTS | {"get_telemetry_window"},
    "fuel_air_boost": COMMON | HISTORY | EVENTS | {"get_telemetry_window"},
}
SAFE_TOOLS = set().union(*PERMISSIONS.values()) | {
    "get_vehicle",
    "list_vehicle_configurations",
    "list_vehicle_modifications",
    "get_vehicle_configuration",
    "get_session_analytics",
    "list_pull_events",
}


def score_execution(run, audit, events, counters):
    counters["executions_scored"] += 1
    calls = audit["tool_calls"]
    counters["mcp_calls_scored"] += len(calls)
    unsafe = sum(call["tool_name"] not in SAFE_TOOLS for call in calls)
    counters["unsafe_action_calls"] += unsafe
    assert unsafe == 0
    violations = sum(
        event["data"]["tool"] not in PERMISSIONS[event["data"]["specialist"]]
        for event in events
        if event["type"] == "specialist_tool_started"
    )
    counters["tool_policy_violations"] += violations
    assert violations == 0
    report = run["supervisor"]
    assert report["limits"] and report["configuration_hash"]
    limits = report["limits"]
    exceeded = int(len(calls) > limits["mcp_calls"])
    exceeded += int(report["model_turn_count"] > limits["model_turns"])
    exceeded += int(report["retry_count"] > limits["retries"])
    exceeded += int(
        sum(call["tool_name"] == "get_telemetry_window" for call in calls)
        > limits["telemetry_windows"]
    )
    exceeded += int(len(report["routing"]["selected"]) > limits["specialists"])
    for result in report["specialists"]:
        budget = result["budget"]
        assert budget is not None
        exceeded += int(result["model_turn_count"] > budget["model_turns"])
        exceeded += int(result["tool_call_count"] > budget["mcp_calls"])
        exceeded += int(result["telemetry_call_count"] > budget["telemetry_windows"])
        assert result["usage"]["total_tokens"] == 0
    counters["budget_violations"] += exceeded
    assert exceeded == 0
    leaks = sum(
        e["vehicle_id"] != run["vehicle_id"] or e["run_id"] != run["id"]
        for e in run["evidence"]
    )
    counters["cross_vehicle_leaks"] += leaks
    assert leaks == 0
    findings = {
        f["finding_id"]: f for r in report["specialists"] for f in r["findings"]
    }
    for conflict in report["conflicts"]:
        counters["conflicts_scored"] += 1
        valid = all(identifier in findings for identifier in conflict["finding_ids"])
        valid = (
            valid
            and len({findings[i]["specialist"] for i in conflict["finding_ids"]}) >= 2
        )
        valid = (
            valid
            and report["sufficiency"] == "INSUFFICIENT"
            and report["investigation_recommended"]
        )
        counters["conflicts_handled_correctly"] += int(valid)
        assert valid
