"""Run-scoped documentary tools, independent of vehicle MCP and arbitrary web access."""

import asyncio
import re
from enum import StrEnum
from uuid import UUID

from vehicle_platform.knowledge.domain import (
    DocumentVersion,
    KnowledgeEvidence,
    KnowledgeNeed,
    Model,
    RetrievalIntent,
    RetrievalResult,
    Topic,
    VehicleScope,
)
from vehicle_platform.knowledge.retrieval import KnowledgeService


class RequestType(StrEnum):
    VEHICLE_FACT = "VEHICLE_FACT"
    KNOWLEDGE_FACT = "KNOWLEDGE_FACT"
    HYBRID_COMPARISON = "HYBRID_COMPARISON"
    TECHNICAL_KNOWLEDGE_INSUFFICIENT = "TECHNICAL_KNOWLEDGE_INSUFFICIENT"
    VEHICLE_EVIDENCE_INSUFFICIENT = "VEHICLE_EVIDENCE_INSUFFICIENT"


class KnowledgePlan(Model):
    request_type: RequestType
    intent: RetrievalIntent | None = None


def source_tuner_for(question: str) -> str | None:
    if re.search(r"\bmhd\b", question, re.I):
        return "MHD"
    if re.search(r"\b(bootmod3|customrom)\b", question, re.I):
        return "bootmod3"
    return None


def plan(question: str) -> KnowledgePlan:
    """Only explicit documentary/interpretive intent requires knowledge; measurements stay MCP."""
    q = question.casefold()
    technical = bool(
        re.search(
            r"\b(how does|how do|explain|documentation|documentação|technical reference|"
            r"specification|especificação|operating principle|como funciona|princípio)\b",
            q,
        )
    )
    technical = technical or bool(
        re.search(r"\b(target|alvo|service limit|documented|oem reference)\b", q)
        and re.search(r"hpfp|lpfp|fuel|rail|boost|stage|tune|map|pressão|torque|ignition", q)
        and not re.search(r"\b(recorded|observed|commanded|measured|session|last pull)\b", q)
    )
    if not re.search(
        r"\b(my|meu|minha|recorded|observed|session|sessão|this vehicle|this car|last pull)\b", q
    ):
        technical = technical or bool(
            re.search(r"\b(what|which|does|can|why|qual|quais|como)\b", q)
            and re.search(
                r"n55|hpfp|lpfp|dme|engine|fuel|rail|valvetronic|turbo|boost|intercool|"
                r"compression|cooling|stage|tune|map|stock|sensor|motronic|ignition|torque|knock",
                q,
            )
        )
    hybrid = bool(
        re.search(
            r"\b(expected|normal|cause|caused|causar|causou|esperado|esperada|within spec|"
            r"healthy|saudável)\b",
            q,
        )
    )
    hybrid = hybrid or bool(
        re.search(r"\b(compare|comparison|versus|comparar)\b", q)
        and re.search(r"\b(reference|oem|documented|target|specification|alvo)\b", q)
    )
    measured = bool(
        re.search(
            r"\b(recorded|observed|measured|commanded|session|sessão|last pull|registrad[oa])\b", q
        )
    )
    measured = measured or bool(re.search(r"\b(why did|why was|during (?:a|the) pull)\b", q))
    explicit_documentation = bool(
        re.search(
            r"\b(documentation|documentação|reference|referência|oem|specification|especificação|"
            r"operating principle|princípio|como funciona)\b",
            q,
        )
    )
    measured = measured or bool(
        re.search(r"\b(missing|unknown|absent|not recorded)\b", q)
        and re.search(r"\b(pressure|boost|iat|rpm|throttle|lambda|telemetry|signal)\b", q)
        and not explicit_documentation
        and not re.search(r"\b(target|limit|tuner|map|calibration)\b", q)
    )
    if measured and not hybrid:
        if explicit_documentation:
            hybrid = True
        else:
            # "Explain/how does" can introduce a question about recorded measurements.
            # It must not terminate early with a documentary-only answer.
            technical = False
    topic: Topic = (
        "fuel"
        if re.search(r"hpfp|lpfp|fuel|rail|combustível|pressão.*alta", q)
        else "thermal"
        if re.search(r"iat|intercooler|thermal|cool|oil|temperatur|óleo", q)
        else "boost"
        if re.search(r"boost|turbo|wastegate|throttle|carga", q)
        else "calibration"
        if re.search(r"stage|tune|calibra|octan|map", q)
        else "architecture"
    )
    if not technical and not hybrid:
        return KnowledgePlan(request_type=RequestType.VEHICLE_FACT)
    need: KnowledgeNeed = (
        "normative_target"
        if re.search(r"target|limit|normal|expected|esperad|especific|alvo", q)
        else "principle"
    )
    return KnowledgePlan(
        request_type=RequestType.HYBRID_COMPARISON if hybrid else RequestType.KNOWLEDGE_FACT,
        intent=RetrievalIntent(
            query=question[:1000], topic=topic, need=need, source_tuner=source_tuner_for(question)
        ),
    )


SPECIALIST_TOPICS = {
    "performance": frozenset({"calibration", "architecture", "boost"}),
    "thermal": frozenset({"thermal"}),
    "fuel_air_boost": frozenset({"fuel", "boost", "calibration"}),
    "data_quality": frozenset(),
    "supervisor": frozenset(
        {"architecture", "fuel", "boost", "thermal", "calibration", "diagnostics"}
    ),
}


class KnowledgeTools:
    """Host supplies immutable MCP-derived scope. Provider supplies only bounded intent.

    Each instance belongs to one run and effective session context. Metadata/evidence reads may
    resolve only evidence already retrieved by that same instance. No arbitrary URLs or files.
    """

    def __init__(self, service: KnowledgeService, scope: VehicleScope) -> None:
        self.service, self.scope = service, scope
        self.calls = 0
        self.results: list[RetrievalResult] = []
        self._evidence: dict[UUID, KnowledgeEvidence] = {}

    async def search_technical_knowledge(
        self, intent: RetrievalIntent, specialist: str
    ) -> RetrievalResult:
        if intent.topic not in SPECIALIST_TOPICS.get(specialist, frozenset()):
            raise ValueError("knowledge_specialist_scope_violation")
        if self.calls >= 3:
            raise ValueError("knowledge_call_budget_exhausted")
        self.calls += 1
        async with asyncio.timeout(8):
            result = await self.service.search(intent, self.scope)
        if len(result.model_dump_json().encode()) > 49152:
            raise ValueError("knowledge_result_budget_exhausted")
        self.results.append(result)
        self._evidence.update({item.id: item for item in result.evidence})
        return result

    def get_knowledge_evidence(self, evidence_id: UUID) -> KnowledgeEvidence:
        if evidence_id not in self._evidence:
            raise ValueError("unknown_current_run_knowledge_evidence")
        return self._evidence[evidence_id].model_copy(deep=True)

    def get_knowledge_document(self, evidence_id: UUID) -> DocumentVersion:
        return self.get_knowledge_evidence(evidence_id).document

    def for_specialist(self, specialist: str) -> list[KnowledgeEvidence]:
        allowed = SPECIALIST_TOPICS.get(specialist, frozenset())
        return [
            item
            for result in self.results
            if result.intent.topic in allowed
            for item in result.evidence
        ]
