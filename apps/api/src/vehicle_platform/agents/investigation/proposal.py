"""Validate provider semantic proposals before creating public artifacts."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from vehicle_platform.agents.investigation.domain import (
    EvidenceGap,
    GapType,
    Hypothesis,
    HypothesisCategory,
    Resolution,
    SignalNeed,
    SignalRole,
)
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun, StrictModel


@dataclass(frozen=True)
class InvestigationInput:
    question: str
    context: dict[str, Any]
    evidence: list[dict[str, Any]]
    missing_evidence: list[str]


class ProposedHypothesis(StrictModel):
    category: HypothesisCategory
    evidence_for: list[UUID] = Field(default_factory=list, max_length=8)
    evidence_against: list[UUID] = Field(default_factory=list, max_length=8)


class ProposedGap(StrictModel):
    category: GapType
    hypothesis_indexes: list[int] = Field(default_factory=list, max_length=5)
    required: bool = True
    signal_roles: list[SignalRole] = Field(default_factory=list, max_length=6)
    resolution: Resolution = Resolution.MEDIUM


class InvestigationProposal(StrictModel):
    hypotheses: list[ProposedHypothesis] = Field(default_factory=list, max_length=5)
    gaps: list[ProposedGap] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def discriminating_gaps(self) -> "InvestigationProposal":
        if len({hypothesis.category for hypothesis in self.hypotheses}) != len(self.hypotheses):
            raise ValueError("duplicate hypothesis category")
        for gap in self.gaps:
            if any(index < 0 or index >= len(self.hypotheses) for index in gap.hypothesis_indexes):
                raise ValueError("gap references unknown hypothesis")
            if gap.category is GapType.TECHNICAL_DOCUMENTATION and gap.signal_roles:
                raise ValueError("technical documentation cannot become a telemetry recipe")
            if (
                gap.category not in {GapType.SIGNAL_OR_MEASUREMENT, GapType.DATA_QUALITY}
                and gap.signal_roles
            ):
                raise ValueError("only measurement or quality gaps can require signals")
        for index in range(len(self.hypotheses)):
            if not any(index in gap.hypothesis_indexes for gap in self.gaps):
                raise ValueError("hypothesis lacks a discriminating gap")
        if sum(len(set(gap.signal_roles)) for gap in self.gaps) > 16:
            raise ValueError("signal need budget exceeded")
        return self


HYPOTHESIS_TEXT: dict[HypothesisCategory, tuple[str, str]] = {
    HypothesisCategory.THERMAL: (
        "Thermal conditions may be associated with the observed change",
        "Compare measured temperatures across compatible operating windows",
    ),
    HypothesisCategory.AIRFLOW_BOOST: (
        "Measured boost behavior may differ across comparable windows",
        "Compare recorded boost and operating context without inferring a component failure",
    ),
    HypothesisCategory.FUELING: (
        "Available fueling measurements may differ across comparable windows",
        "Compare measured pressure and mixture where the source supports them",
    ),
    HypothesisCategory.THROTTLE_TORQUE_INTERVENTION: (
        "Throttle or torque behavior may differ across comparable windows",
        "Compare available throttle context and mark unavailable intervention signals",
    ),
    HypothesisCategory.DATA_QUALITY: (
        "Data quality may explain the apparent difference",
        "Check gaps, sequence, sampling and signal availability before interpretation",
    ),
    HypothesisCategory.CONFIGURATION_ASSOCIATION: (
        "The observed change may be associated with a configuration boundary",
        "Compare compatible pre and post configuration data and preserve confounders",
    ),
    HypothesisCategory.PERFORMANCE_VARIATION: (
        "Measured performance may vary across comparable windows",
        "Compare repeated window duration under recorded comparable conditions",
    ),
    HypothesisCategory.UNKNOWN_OTHER: (
        "The current evidence may not distinguish the observed variation",
        "Find a measurable difference that can separate candidate explanations",
    ),
}

GAP_TEXT: dict[GapType, tuple[str, str]] = {
    GapType.SIGNAL_OR_MEASUREMENT: (
        "A relevant measurement is absent or incomplete",
        "The candidate explanations need a measured discriminator",
    ),
    GapType.COMPARABLE_HISTORY: (
        "Comparable historical data is insufficient",
        "The observed difference needs compatible sessions or windows",
    ),
    GapType.TECHNICAL_DOCUMENTATION: (
        "A technical document is needed to establish the reference value",
        "Telemetry cannot establish a manufacturer's documentary specification",
    ),
    GapType.DATA_QUALITY: (
        "Recorded data quality limits interpretation",
        "Signal gaps, sparse sampling or sequence errors can mimic vehicle behavior",
    ),
    GapType.CONFIGURATION_CONTEXT: (
        "Configuration context is incomplete",
        "Comparison requires the effective vehicle configuration at each session",
    ),
    GapType.MECHANICAL_CAUSE: (
        "Mechanical cause is not established",
        "Observed telemetry alone cannot identify a failed component",
    ),
}


def materialize(
    proposal: InvestigationProposal, run: AgentRun
) -> tuple[list[Hypothesis], list[EvidenceGap], list[SignalNeed]]:
    """Use only exact evidence IDs from the completed source run and fixed public language."""
    if run.status != "completed" or run.result is None:
        raise AgentError("invalid_investigation_run")
    current = {
        evidence.id: evidence
        for evidence in run.evidence
        if evidence.run_id == run.id and evidence.vehicle_id == run.vehicle_id
    }
    hypotheses: list[Hypothesis] = []
    for proposed in proposal.hypotheses:
        for identifier in proposed.evidence_for + proposed.evidence_against:
            if identifier not in current:
                raise AgentError("unknown_evidence")
            if current[identifier].warnings or current[identifier].truncated:
                raise AgentError("low_quality_hypothesis_evidence")
        statement, goal = HYPOTHESIS_TEXT[proposed.category]
        hypotheses.append(
            Hypothesis(
                id=uuid4(),
                category=proposed.category,
                statement=statement,
                discriminating_goal=goal,
                evidence_for=proposed.evidence_for,
                evidence_against=proposed.evidence_against,
            )
        )
    gaps: list[EvidenceGap] = []
    needs: list[SignalNeed] = []
    for proposed_gap in proposal.gaps:
        gap_id = uuid4()
        linked = [hypotheses[index].id for index in proposed_gap.hypothesis_indexes]
        description, rationale = GAP_TEXT[proposed_gap.category]
        gap_needs = [
            SignalNeed(
                id=uuid4(),
                role=role,
                required=proposed_gap.required,
                resolution=proposed_gap.resolution,
                gap_ids=[gap_id],
                hypothesis_ids=linked,
            )
            for role in dict.fromkeys(proposed_gap.signal_roles)
        ]
        needs.extend(gap_needs)
        gaps.append(
            EvidenceGap(
                id=gap_id,
                category=proposed_gap.category,
                description=description,
                why_it_matters=rationale,
                hypothesis_ids=linked,
                required=proposed_gap.required,
                signal_need_ids=[need.id for need in gap_needs],
            )
        )
        for index in proposed_gap.hypothesis_indexes:
            hypotheses[index].missing_gap_ids.append(gap_id)
    return hypotheses, gaps, needs
