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

    def completed(self, run: AgentRun) -> None:
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
