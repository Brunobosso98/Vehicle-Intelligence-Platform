"""Deterministic, trust/applicability-aware hybrid retrieval with auditable citations."""

import re
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any
from uuid import uuid4

from vehicle_platform.knowledge.domain import (
    DocumentChunk,
    DocumentVersion,
    KnowledgeEvidence,
    KnowledgeSource,
    RetrievalIntent,
    RetrievalResult,
    SourceConflict,
    Trust,
    VehicleScope,
    match,
    scope_hash,
)
from vehicle_platform.knowledge.repository import KnowledgeRepository
from vehicle_platform.knowledge.security import quarantine_text
from vehicle_platform.observability.telemetry import Telemetry

QueryEncoder = Callable[[str, str], Awaitable[list[float] | None]]
TRUST_WEIGHT = {
    Trust.TIER_1_AUTHORITATIVE: 1.0,
    Trust.TIER_2_STRONG_TECHNICAL: 0.9,
    Trust.TIER_3_CURATED_INTERNAL: 0.6,
    Trust.TIER_4_COMMUNITY: 0.0,
}


def exactness(query: str, text: str) -> float:
    words = set(re.findall(r"[a-z0-9]+", query.casefold()))
    terms = set(re.findall(r"[a-z0-9]+", text.casefold()))
    return len(words & terms) / max(1, len(words))


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        telemetry: Telemetry,
        encoder: QueryEncoder | None = None,
        redact: Callable[[str], str] | None = None,
    ) -> None:
        self.repository, self.telemetry, self.encoder = repository, telemetry, encoder
        self.redact: Callable[[str], str] = redact or (lambda value: value)
        self._cache: OrderedDict[
            tuple[str, str, str, str], tuple[float, list[dict[str, Any]], bool]
        ] = OrderedDict()
        meter = telemetry.metrics.get_meter("vehicle_platform.knowledge")
        self.requests = meter.create_counter("retrieval_requests_total")
        self.latency = meter.create_histogram("retrieval_latency_seconds")
        self.candidate_counter = meter.create_counter("retrieval_candidates_total")
        self.gaps = meter.create_counter("retrieval_knowledge_gap_total")
        self.rejected = meter.create_counter("retrieval_wrong_platform_rejections_total")
        self.cache_hits = meter.create_counter("retrieval_cache_hits_total")

    async def search(self, intent: RetrievalIntent, scope: VehicleScope) -> RetrievalResult:
        intent = RetrievalIntent.model_validate_json(self.redact(intent.model_dump_json()))
        scope = VehicleScope.model_validate_json(self.redact(scope.model_dump_json()))
        self.requests.add(1, {"topic": intent.topic})
        with self.telemetry.tracer.start_as_current_span(
            "knowledge.retrieval", record_exception=False, set_status_on_exception=False
        ):
            return await self._search(intent, scope)

    async def _search(self, intent: RetrievalIntent, scope: VehicleScope) -> RetrievalResult:
        started = perf_counter()
        index = await self.repository.active_index()
        if index is None:
            self.gaps.add(1, {"topic": intent.topic})
            self.latency.record(perf_counter() - started)
            return RetrievalResult(
                id=uuid4(),
                index_id="unavailable",
                scope=scope,
                intent=intent,
                knowledge_gaps=["knowledge_index_unavailable"],
                candidate_count=0,
                latency_seconds=perf_counter() - started,
            )
        revision = await self.repository.retrieval_revision()
        cache_key = (intent.model_dump_json(), scope_hash(scope), index.id, revision)
        selection = perf_counter()
        rows: list[dict[str, Any]]
        requested_engines = {
            code[:3].casefold()
            for code in re.findall(r"\b[NBMS]\d{2}(?:[A-Z]\d{2}[A-Z0-9]*)?\b", intent.query, re.I)
        }
        engine_mismatch = bool(
            scope.engine
            and requested_engines
            and scope.engine[:3].casefold() not in requested_engines
        )
        cached = self._cache.get(cache_key)
        cache_hit = cached is not None and selection - cached[0] < 30
        if engine_mismatch:
            # An explicit query identifier cannot override the MCP-derived vehicle engine.
            # Generic vector neighbors do not resolve this conflict, and need no paid encoding.
            rows, vector_available = [], False
        elif cached is not None and cache_hit:
            _, rows, vector_available = cached
            self._cache.move_to_end(cache_key)
            self.cache_hits.add(1)
        else:
            vector = await self.encoder(intent.query, index.id) if self.encoder else None
            vector_available = vector is not None
            with self.telemetry.tracer.start_as_current_span(
                "knowledge.lexical_vector", record_exception=False, set_status_on_exception=False
            ):
                rows = await self.repository.candidates(
                    scope, intent.query, index.id, vector, intent.topic, intent.source_tuner
                )
            self._cache[cache_key] = (perf_counter(), rows, vector_available)
            self._cache.move_to_end(cache_key)
            while len(self._cache) > 64:
                self._cache.popitem(last=False)
        timings = {"candidate_selection": perf_counter() - selection}
        with self.telemetry.tracer.start_as_current_span(
            "knowledge.fusion_rerank", record_exception=False, set_status_on_exception=False
        ):
            lexical_order = sorted(
                (r for r in rows if r["lexical_score"] > 0),
                key=lambda r: (-r["lexical_score"], str(r["id"])),
            )
            vector_order = sorted(
                (r for r in rows if r["vector_score"] is not None and r["vector_score"] > 0.2),
                key=lambda r: (-r["vector_score"], str(r["id"])),
            )
            lex_rank = {r["id"]: i + 1 for i, r in enumerate(lexical_order)}
            vec_rank = {r["id"]: i + 1 for i, r in enumerate(vector_order)}
            run_id = uuid4()
            evidence: list[KnowledgeEvidence] = []
            rejected = 0
            rank_start = perf_counter()
            for row in rows:
                doc = DocumentVersion.model_validate(row["document"])
                source = KnowledgeSource.model_validate(row["source"])
                chunk = DocumentChunk.model_validate(row["chunk"])
                applicability = match(doc.applicability, scope)
                if applicability.status == "INCOMPATIBLE":
                    rejected += 1
                    continue
                if intent.topic not in doc.applicability.subsystems:
                    continue
                text = source.model_dump_json() + doc.model_dump_json() + chunk.text
                if quarantine_text(text) or self.redact(text) != text:
                    continue
                lex = 1 / (60 + lex_rank[row["id"]]) if row["id"] in lex_rank else 0
                vec = 1 / (60 + vec_rank[row["id"]]) if row["id"] in vec_rank else 0
                quality = 0.4 if chunk.quality == "ambiguous" else 1
                score = (
                    (lex + vec)
                    * TRUST_WEIGHT[source.trust]
                    * applicability.score
                    * quality
                    * (
                        0.25
                        + 0.75
                        * exactness(
                            intent.query,
                            " ".join(
                                [
                                    source.publisher,
                                    doc.title,
                                    doc.applicability.tuner or "",
                                    *chunk.heading_path,
                                    chunk.text,
                                ]
                            ),
                        )
                    )
                )
                evidence.append(
                    KnowledgeEvidence(
                        id=uuid4(),
                        retrieval_run_id=run_id,
                        index_id=index.id,
                        vehicle_id=scope.vehicle_id,
                        scope_hash=scope_hash(scope),
                        source=source,
                        document=doc,
                        chunk_id=chunk.id,
                        chunk_checksum=chunk.checksum,
                        page=chunk.page,
                        section=chunk.section,
                        heading_path=chunk.heading_path,
                        snippet=chunk.text[:800],
                        applicability=applicability,
                        lexical_score=float(row["lexical_score"]),
                        vector_score=float(row["vector_score"])
                        if row["vector_score"] is not None
                        else None,
                        fused_score=score,
                        quality=chunk.quality,
                        numeric_facts=chunk.numeric_facts,
                    )
                )
            conflicts = await self.repository.conflicts(
                [e.document.id for e in evidence], intent.topic
            )
            for item in evidence:
                item.conflict_ids = [
                    c["id"]
                    for c in conflicts
                    if item.document.id in {c["left_version_id"], c["right_version_id"]}
                ]
                if item.conflict_ids:
                    item.fused_score *= 0.8
            evidence.sort(key=lambda e: (-e.fused_score, str(e.chunk_id)))
            evidence = evidence[: intent.top_k]
            final_versions = {item.document.id for item in evidence}
            conflicts = [
                c
                for c in conflicts
                if {c["left_version_id"], c["right_version_id"]} & final_versions
            ]
            gaps: list[str] = []
            if engine_mismatch:
                gaps.append("query_engine_scope_mismatch")
            if not evidence:
                gaps.append("trusted_applicable_documentation_unavailable")
            elif not any(
                e.source.trust in {Trust.TIER_1_AUTHORITATIVE, Trust.TIER_2_STRONG_TECHNICAL}
                and e.quality != "ambiguous"
                for e in evidence
            ):
                gaps.append("authoritative_reference_unavailable")
            elif (
                scope.engine
                and re.search(
                    r"\b" + re.escape(scope.engine) + r"\b|\b(this vehicle|my vehicle)\b",
                    intent.query,
                    re.I,
                )
                and not any(e.document.applicability.engine for e in evidence)
            ):
                gaps.append("engine_specific_reference_unavailable")
            if intent.need == "normative_target" and not any(
                has_normative_target(e, intent.topic, scope) for e in evidence
            ):
                gaps.append("applicable_normative_reference_unavailable")
            if (
                intent.need == "normative_target"
                and scope.calibration != "stock"
                and (not scope.tuner or not scope.map_version)
            ):
                gaps.append("exact_tuner_map_target_unavailable")
            if conflicts:
                gaps.append("unresolved_source_conflict")
            timings["fusion_rerank"] = perf_counter() - rank_start
        with self.telemetry.tracer.start_as_current_span(
            "knowledge.evidence", record_exception=False, set_status_on_exception=False
        ):
            result = RetrievalResult(
                id=run_id,
                index_id=index.id,
                scope=scope,
                intent=intent,
                evidence=evidence,
                knowledge_gaps=gaps,
                source_conflicts=[
                    SourceConflict.model_validate(
                        item | {"explanation": self.redact(item["explanation"])}
                    )
                    for item in conflicts
                ],
                candidate_count=len(rows),
                wrong_platform_rejections=rejected,
                vector_available=vector_available,
                latency_seconds=perf_counter() - started,
                timings=timings,
            )
        await self.repository.audit(result)
        self.candidate_counter.add(len(rows))
        self.rejected.add(rejected)
        self.latency.record(result.latency_seconds)
        if gaps:
            self.gaps.add(1, {"topic": intent.topic})
        self.telemetry.log(
            "knowledge.retrieved",
            str(run_id),
            index_version=index.id,
            candidates=len(rows),
            knowledge_gap=bool(gaps),
        )
        return result


def validate_numeric(
    evidence: KnowledgeEvidence, value: float, unit: str, conditions: str, scope: VehicleScope
) -> None:
    if (
        evidence.vehicle_id != scope.vehicle_id
        or evidence.scope_hash != scope_hash(scope)
        or not evidence.eligible
        or not match(evidence.document.applicability, scope).normative
        or evidence.quality != "reviewed"
    ):
        raise ValueError("Ineligible normative knowledge evidence")
    matching = [
        f
        for f in evidence.numeric_facts
        if f.kind != "descriptive"
        and f.value == value
        and f.unit == unit
        and f.conditions == conditions
        and f.original in evidence.snippet
        and f.conditions in evidence.snippet
    ]
    if not matching:
        raise ValueError("Numeric knowledge requires exact reviewed value/unit/conditions")
    fact = matching[0]
    calibration = evidence.document.applicability.calibration
    if (
        fact.kind == "stock_target" and (calibration != "stock" or scope.calibration != "stock")
    ) or (
        fact.kind == "tune_target"
        and (calibration != "tune_specific" or not scope.tuner or not scope.map_version)
    ):
        raise ValueError("Numeric target calibration does not match the vehicle")


def has_normative_target(evidence: KnowledgeEvidence, topic: str, scope: VehicleScope) -> bool:
    for fact in evidence.numeric_facts:
        if fact.kind == "descriptive" or fact.topic != topic:
            continue
        try:
            validate_numeric(evidence, fact.value, fact.unit, fact.conditions, scope)
        except ValueError:
            continue
        return True
    return False
