from vehicle_platform.agents.schemas import AgentRun
from vehicle_platform.observability.telemetry import Telemetry


class AgentInstrumentation:
    def __init__(self, telemetry: Telemetry) -> None:
        self.telemetry = telemetry
        meter = telemetry.metrics.get_meter("vehicle_platform.agents")
        self.runs = meter.create_counter("agent.runs")
        self.errors = meter.create_counter("agent.run.errors")
        self.duration = meter.create_histogram("agent.run.duration", unit="s")
        self.tools = meter.create_counter("agent.tool.calls")
        self.tool_errors = meter.create_counter("agent.tool.errors")
        self.tool_duration = meter.create_histogram("agent.tool.duration", unit="s")
        self.grounding = meter.create_counter("agent.grounding.failures")
        self.budgets = meter.create_counter("agent.budget.exhaustions")
        self.input_tokens = meter.create_counter("agent.input.tokens")
        self.output_tokens = meter.create_counter("agent.output.tokens")
        self.active = meter.create_up_down_counter("agent.active.runs")
        self.supervisors = meter.create_counter("supervisor.runs")
        self.routing = meter.create_counter("supervisor.routing")
        self.selected = meter.create_histogram("supervisor.specialists.selected")
        self.specialists = meter.create_counter("specialist.runs")
        self.specialist_failures = meter.create_counter("specialist.failures")
        self.specialist_duration = meter.create_histogram("specialist.duration", unit="s")
        self.specialist_tools = meter.create_counter("specialist.tool.calls")
        self.conflicts = meter.create_counter("supervisor.conflicts")
        self.insufficient = meter.create_counter("supervisor.insufficient")
        self.escalations = meter.create_counter("supervisor.phase7b.proposals")
        self.cache_hits = meter.create_counter("supervisor.evidence.cache.hits")
        self.policy_rejections = meter.create_counter("specialist.tool.policy.rejections")

    def completed(self, run: AgentRun) -> None:
        if run.supervisor:
            report = run.supervisor
            self.specialist_failures.add(0, {})
            self.policy_rejections.add(0, {})
            self.supervisors.add(1, {"status": run.status})
            self.routing.add(1, {"intent": report.routing.intent.value})
            self.selected.record(len(report.routing.selected))
            self.conflicts.add(len(report.conflicts))
            self.cache_hits.add(report.cache_hits)
            if report.investigation_recommended:
                self.insufficient.add(1, {"sufficiency": report.sufficiency.value})
                self.escalations.add(1)
            for result in report.specialists:
                attributes = {"specialist": result.specialist.value, "status": result.status}
                self.specialists.add(1, attributes)
                self.specialist_duration.record(result.duration_seconds, attributes)
                self.specialist_tools.add(result.tool_call_count, attributes)
                if result.status not in {"completed", "skipped"}:
                    self.specialist_failures.add(1, attributes)
                if result.error_category == "specialist_tool_policy_violation":
                    self.policy_rejections.add(1, attributes)
                if result.error_category and "budget" in result.error_category:
                    self.budgets.add(1, {"scope": result.specialist.value})
                self.telemetry.log(
                    "supervisor.specialist.completed",
                    str(run.id),
                    agent_run_id=str(run.id),
                    specialist=result.specialist.value,
                    status=result.status,
                    tool_call_count=result.tool_call_count,
                    duration_seconds=result.duration_seconds,
                    error_code=result.error_category,
                    conflict_count=len(report.conflicts),
                    sufficiency=report.sufficiency.value,
                    phase7b_proposed=report.investigation_recommended,
                )
        self.runs.add(1, {"status": run.status, "provider": run.provider})
        self.duration.record(run.duration_seconds or 0, {"provider": run.provider})
        if run.error_category:
            self.errors.add(1, {"category": run.error_category})
            if "budget" in run.error_category:
                self.budgets.add(1)
        if run.usage.input_tokens is not None:
            self.input_tokens.add(run.usage.input_tokens, {"provider": run.provider})
        if run.usage.output_tokens is not None:
            self.output_tokens.add(run.usage.output_tokens, {"provider": run.provider})
        self.telemetry.log(
            "agent.run.completed",
            str(run.id),
            agent_run_id=str(run.id),
            provider=run.provider,
            model=run.model,
            status=run.status,
            error_code=run.error_category,
            duration_seconds=run.duration_seconds,
            input_tokens=run.usage.input_tokens,
            output_tokens=run.usage.output_tokens,
        )
