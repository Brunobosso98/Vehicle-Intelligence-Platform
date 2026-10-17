"""Host-validated documentary references, including reviewed conditional numeric facts."""

import re
from uuid import uuid4

from vehicle_platform.knowledge.domain import (
    KnowledgeClaim,
    KnowledgeEvidence,
    KnowledgeReport,
    NumericFact,
    RetrievalResult,
    SourceStatus,
    Trust,
    scope_hash,
)
from vehicle_platform.knowledge.retrieval import validate_numeric


def documentary_eligible(evidence: KnowledgeEvidence) -> bool:
    return not (
        evidence.source.status != SourceStatus.VERIFIED
        or evidence.source.trust not in {Trust.TIER_1_AUTHORITATIVE, Trust.TIER_2_STRONG_TECHNICAL}
        or evidence.document.status not in {"EXTRACTED", "INDEXED"}
        or evidence.quality == "ambiguous"
        or evidence.conflict_ids
        or evidence.applicability.status == "INCOMPATIBLE"
    )


def reference_claim(evidence: KnowledgeEvidence) -> KnowledgeClaim | None:
    if not documentary_eligible(evidence):
        return None
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", evidence.snippet):
        if 30 <= len(sentence) <= 350 and not re.search(r"(?<!\w)\d", sentence):
            return KnowledgeClaim(id=uuid4(), evidence_id=evidence.id, excerpt=sentence)
    return None


def numeric_reference(
    evidence: KnowledgeEvidence, result: RetrievalResult
) -> KnowledgeClaim | None:
    if not documentary_eligible(evidence) or evidence.quality != "reviewed":
        return None
    for fact in evidence.numeric_facts:
        if fact.topic != result.intent.topic:
            continue
        if fact.original not in evidence.snippet or fact.conditions not in evidence.snippet:
            continue
        normative = result.intent.need == "normative_target"
        if normative:
            if fact.kind == "descriptive" or fact.topic != result.intent.topic:
                continue
            try:
                validate_numeric(evidence, fact.value, fact.unit, fact.conditions, result.scope)
            except ValueError:
                continue
        return KnowledgeClaim(
            id=uuid4(),
            evidence_id=evidence.id,
            excerpt=fact.original,
            numeric_fact=fact,
            normative=normative,
        )
    return None


def validate_reference(claim: KnowledgeClaim, result: RetrievalResult) -> KnowledgeEvidence:
    evidence = next((e for e in result.evidence if e.id == claim.evidence_id), None)
    if (
        not evidence
        or evidence.retrieval_run_id != result.id
        or evidence.vehicle_id != result.scope.vehicle_id
        or evidence.scope_hash != scope_hash(result.scope)
        or claim.excerpt not in evidence.snippet
        or not documentary_eligible(evidence)
    ):
        raise ValueError("invalid_documentary_claim")
    if claim.numeric_fact is not None:
        fact = NumericFact.model_validate(claim.numeric_fact.model_dump())
        if (
            fact not in evidence.numeric_facts
            or claim.excerpt != fact.original
            or fact.conditions not in evidence.snippet
            or evidence.quality != "reviewed"
        ):
            raise ValueError("invalid_numeric_documentary_reference")
        if claim.normative:
            if fact.kind == "descriptive" or fact.topic != result.intent.topic:
                raise ValueError("descriptive_fact_is_not_a_normative_target")
            validate_numeric(evidence, fact.value, fact.unit, fact.conditions, result.scope)
    elif claim.normative or len(claim.excerpt) < 20 or re.search(r"(?<!\w)\d", claim.excerpt):
        raise ValueError("unreviewed_numeric_knowledge_claim")
    return evidence


def report(
    result: RetrievalResult, *, hybrid: bool, vehicle_evidence_available: bool = True
) -> KnowledgeReport:
    claims = []
    for item in result.evidence:
        claim = numeric_reference(item, result) or reference_claim(item)
        if claim is not None:
            claims.append(claim)
    for claim in claims:
        validate_reference(claim, result)
    return KnowledgeReport(
        request_type="VEHICLE_EVIDENCE_INSUFFICIENT"
        if hybrid and not vehicle_evidence_available
        else "TECHNICAL_KNOWLEDGE_INSUFFICIENT"
        if result.knowledge_gaps
        else "HYBRID_COMPARISON"
        if hybrid
        else "KNOWLEDGE_FACT",
        retrieval=result,
        claims=claims,
    )


def render(value: KnowledgeReport) -> str:
    lines = []
    if value.request_type == "VEHICLE_EVIDENCE_INSUFFICIENT":
        lines.append(
            "As evidências do veículo são insuficientes para comparar o comportamento observado. "
            "As referências documentais não estabelecem medições do veículo."
        )
    for claim in value.claims:
        evidence = validate_reference(claim, value.retrieval)
        label = (
            "aplicabilidade parcial"
            if evidence.applicability.status != "APPLICABLE"
            else "aplicável"
        )
        prefix = (
            f"Referência documental ({evidence.source.publisher}; {label}; {evidence.section}): "
        )
        if claim.numeric_fact:
            fact = claim.numeric_fact
            designation = "alvo condicional documentado" if claim.normative else "fato documental"
            lines.append(
                prefix + f"{designation}: {fact.original}; unidade: {fact.unit}; "
                f"condição da fonte: “{fact.conditions}”."
            )
            continue
        lines.append(prefix + f"“{claim.excerpt}”")
    if value.retrieval.knowledge_gaps:
        lines.append(
            "A referência técnica disponível é insuficiente para estabelecer o alvo "
            "ou concluir se o comportamento é esperado para esta configuração."
        )
    if "exact_tuner_map_target_unavailable" in value.retrieval.knowledge_gaps:
        lines.append(
            "O alvo específico do tuner/mapa não está disponível. Stage 2 não define "
            "um alvo universal de pressão, boost, ignição ou torque."
        )
    if "unresolved_source_conflict" in value.retrieval.knowledge_gaps:
        lines.append(
            "Há conflito entre referências técnicas; as condições e fontes permanecem separadas."
        )
    return "\n".join(lines)
