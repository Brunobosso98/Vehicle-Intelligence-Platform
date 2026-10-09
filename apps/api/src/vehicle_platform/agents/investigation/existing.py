"""Bounded existing-evidence search through the Phase 6 MCP client."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from vehicle_platform.agents.investigation.domain import (
    EvidenceGap,
    GapStatus,
    GapType,
    SignalNeed,
)
from vehicle_platform.agents.investigation.planning import ROLE_TO_SIGNAL
from vehicle_platform.agents.mcp_client import EvidenceClient
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun


@dataclass(frozen=True)
class ExistingEvidence:
    gaps: tuple[EvidenceGap, ...]
    recorded_by_session: dict[UUID, set[str]]
    mcp_calls: int


def _good_signals(report: dict[str, Any]) -> set[str]:
    available = set(report.get("available_signals", []))
    quality = report.get("signal_quality", [])
    return {
        str(item["signal"])
        for item in quality
        if isinstance(item, dict)
        and item.get("signal") in available
        and isinstance(item.get("actual_hz"), (int, float))
        and item["actual_hz"] > 0
        and isinstance(item.get("missing_ratio"), (int, float))
        and item["missing_ratio"] <= 0.2
    }


def _sufficient_analysis(run: AgentRun, category: GapType) -> bool:
    names = (
        {"get_repeated_pull_analysis", "compare_pulls", "get_cross_session_analytics"}
        if category is GapType.COMPARABLE_HISTORY
        else {"compare_configurations"}
    )
    for evidence in run.evidence:
        if evidence.source_tool not in names or evidence.warnings or evidence.truncated:
            continue
        if any(
            fact.path.endswith("/sufficiency") and fact.value == "sufficient"
            for fact in evidence.facts
        ):
            return True
    return False


async def search_existing(
    run: AgentRun,
    gaps: list[EvidenceGap],
    needs: list[SignalNeed],
    client: EvidenceClient,
) -> ExistingEvidence:
    """Check compatible sessions and persisted deterministic analysis before capture.

    This does not treat one session's absence as hardware incapability. MCP errors
    fail the investigation safely instead of silently triggering a new capture.
    """
    if run.result is None:
        raise AgentError("invalid_investigation_run")
    context = run.result.context
    sessions = [
        session
        for session in context.sessions[:10]
        if session.get("temporal_configuration_valid")
        and str(session.get("configuration_id")) == str(context.active_configuration_id)
        and session.get("status") == "completed"
    ]
    recorded: dict[UUID, set[str]] = {}
    for session in sessions:
        identifier = UUID(str(session["id"]))
        envelope = await client.call(
            "get_session_capabilities",
            {"vehicle_id": str(run.vehicle_id), "session_id": str(identifier)},
        )
        if str(envelope.context.get("vehicle_id")) != str(run.vehicle_id):
            raise AgentError("incompatible_context")
        if not isinstance(envelope.data, dict):
            raise AgentError("invalid_tool_result")
        recorded[identifier] = _good_signals(envelope.data)
    by_id = {need.id: need for need in needs}
    updated: list[EvidenceGap] = []
    for gap in gaps:
        signals = {
            ROLE_TO_SIGNAL[by_id[need_id].role]
            for need_id in gap.signal_need_ids
            if ROLE_TO_SIGNAL[by_id[need_id].role] is not None
        }
        signals.discard(None)
        if gap.category is GapType.TECHNICAL_DOCUMENTATION:
            updated.append(gap)
        elif gap.category in {GapType.COMPARABLE_HISTORY, GapType.CONFIGURATION_CONTEXT}:
            sufficient = _sufficient_analysis(run, gap.category)
            updated.append(
                gap.model_copy(
                    update={
                        "status": GapStatus.AVAILABLE_IN_EXISTING_DATA
                        if sufficient
                        else GapStatus.NEEDS_NEW_CAPTURE
                        if gap.category is GapType.COMPARABLE_HISTORY
                        else GapStatus.OPEN,
                        "resolution_source": "grounded_phase7a_analysis" if sufficient else None,
                    }
                )
            )
        elif signals and any(signals <= available for available in recorded.values()):
            updated.append(
                gap.model_copy(
                    update={
                        "status": GapStatus.AVAILABLE_IN_EXISTING_DATA,
                        "resolution_source": "mcp_session_capabilities",
                    }
                )
            )
        elif gap.category in {GapType.SIGNAL_OR_MEASUREMENT, GapType.DATA_QUALITY}:
            updated.append(gap.model_copy(update={"status": GapStatus.NEEDS_NEW_CAPTURE}))
        else:
            updated.append(gap)
    return ExistingEvidence(tuple(updated), recorded, len(sessions))
