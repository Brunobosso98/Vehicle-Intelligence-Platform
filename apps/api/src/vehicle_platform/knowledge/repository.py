"""Knowledge-owned SQL persistence. All external values are bound parameters."""

import asyncio
import json
import re
from contextlib import nullcontext
from typing import Any
from uuid import UUID

from sqlalchemy import text

from vehicle_platform.infrastructure.database import Database
from vehicle_platform.knowledge.domain import (
    DocumentChunk,
    DocumentVersion,
    KnowledgeIndexVersion,
    KnowledgeSource,
    RetrievalResult,
    SourceConflict,
    VehicleScope,
    validate_vector,
)
from vehicle_platform.observability.telemetry import Telemetry


class KnowledgeRepository:
    def __init__(self, database: Database, telemetry: Telemetry | None = None) -> None:
        self.database = database
        self.telemetry = telemetry

    async def ingest(
        self,
        source: KnowledgeSource,
        document: DocumentVersion,
        chunks: list[DocumentChunk],
        *,
        activate: bool = False,
    ) -> None:
        telemetry = self.telemetry
        span = (
            telemetry.tracer.start_as_current_span(
                "knowledge.ingestion", record_exception=False, set_status_on_exception=False
            )
            if telemetry
            else nullcontext()
        )
        with span:
            try:
                await self._ingest(source, document, chunks, activate=activate)
            except Exception:
                if telemetry:
                    telemetry.knowledge_ingestion_failures.add(1)
                raise
            if telemetry:
                telemetry.knowledge_ingestions.add(1)
                telemetry.knowledge_chunks.add(len(chunks))

    async def _ingest(
        self,
        source: KnowledgeSource,
        document: DocumentVersion,
        chunks: list[DocumentChunk],
        *,
        activate: bool = False,
    ) -> None:
        if source.id != document.source_id or source.version != document.source_version:
            raise ValueError("Source version mismatch")
        if any(c.version_id != document.id for c in chunks):
            raise ValueError("Chunk version mismatch")
        async with asyncio.timeout(10), self.database.session() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:identity))"),
                {"identity": str(document.document_id)},
            )
            old = await session.scalar(
                text("SELECT snapshot FROM knowledge_sources WHERE id=:id AND version=:version"),
                {"id": source.id, "version": source.version},
            )
            source_json = source.model_dump(mode="json")
            if old is not None and old != source_json:
                raise ValueError("Source snapshots are immutable; increment source version")
            await session.execute(
                text("""
                INSERT INTO knowledge_sources(id,version,snapshot)
                VALUES (:id,:version,CAST(:snapshot AS jsonb)) ON CONFLICT DO NOTHING
            """),
                {"id": source.id, "version": source.version, "snapshot": source.model_dump_json()},
            )
            await session.execute(
                text("""
                INSERT INTO knowledge_documents(id,source_id) VALUES (:id,:source)
                ON CONFLICT DO NOTHING
            """),
                {"id": document.document_id, "source": source.id},
            )
            old_document = await session.scalar(
                text("SELECT snapshot FROM knowledge_document_versions WHERE id=:id"),
                {"id": document.id},
            )
            if old_document is not None and old_document != document.model_dump(mode="json"):
                raise ValueError("Document versions are immutable")
            await session.execute(
                text("""
                INSERT INTO knowledge_document_versions
                  (id,document_id,source_id,source_version,checksum,snapshot)
                VALUES (:id,:document,:source,:version,:checksum,CAST(:snapshot AS jsonb))
                ON CONFLICT DO NOTHING
            """),
                {
                    "id": document.id,
                    "document": document.document_id,
                    "source": source.id,
                    "version": source.version,
                    "checksum": document.checksum,
                    "snapshot": document.model_dump_json(),
                },
            )
            for chunk in chunks:
                old_chunk = await session.scalar(
                    text("SELECT snapshot FROM knowledge_chunks WHERE id=:id"), {"id": chunk.id}
                )
                if old_chunk is not None and old_chunk != chunk.model_dump(mode="json"):
                    raise ValueError("Chunks are immutable")
                await session.execute(
                    text("""
                    INSERT INTO knowledge_chunks
                        (id,version_id,ordinal,checksum,snapshot,search_text)
                    VALUES (:id,:version,:ordinal,:checksum,CAST(:snapshot AS jsonb),:search)
                    ON CONFLICT DO NOTHING
                """),
                    {
                        "id": chunk.id,
                        "version": document.id,
                        "ordinal": chunk.ordinal,
                        "checksum": chunk.checksum,
                        "snapshot": chunk.model_dump_json(),
                        "search": " ".join(chunk.heading_path) + "\n" + chunk.text,
                    },
                )
            if activate:
                await session.execute(
                    text("""
                    UPDATE knowledge_documents SET current_version_id=:version,updated_at=now()
                    WHERE id=:id
                """),
                    {"id": document.document_id, "version": document.id},
                )

    async def index(self, index: KnowledgeIndexVersion, *, activate: bool = False) -> None:
        async with asyncio.timeout(5), self.database.session() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('knowledge-index'))"))
            old = await session.scalar(
                text("SELECT snapshot FROM knowledge_indexes WHERE id=:id"), {"id": index.id}
            )
            if old is not None and old != index.model_dump(mode="json"):
                raise ValueError("Index identity is immutable; create an explicit new version")
            await session.execute(
                text("""
                INSERT INTO knowledge_indexes(id,snapshot) VALUES (:id,CAST(:snapshot AS jsonb))
                ON CONFLICT DO NOTHING
            """),
                {"id": index.id, "snapshot": index.model_dump_json()},
            )
            if activate:
                await session.execute(
                    text("UPDATE knowledge_indexes SET active=false WHERE active")
                )
                await session.execute(
                    text("UPDATE knowledge_indexes SET active=true WHERE id=:id"), {"id": index.id}
                )

    async def active_index(self) -> KnowledgeIndexVersion | None:
        async with asyncio.timeout(5), self.database.session() as session:
            result = await session.scalar(
                text("SELECT snapshot FROM knowledge_indexes WHERE active")
            )
            return KnowledgeIndexVersion.model_validate(result) if result else None

    async def activate_corpus(self, index: KnowledgeIndexVersion, versions: list[UUID]) -> None:
        """Publish all document pointers and their complete index in one transaction.

        A crash or missing embedding leaves the previously published corpus available.
        Staging new versions must therefore use ingest(activate=False).
        """
        if not versions or len(versions) != len(set(versions)):
            raise ValueError("A nonempty unique document version set is required")
        async with asyncio.timeout(10), self.database.session() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('knowledge-index'))"))
            stored = await session.scalar(
                text("SELECT snapshot FROM knowledge_indexes WHERE id=:id FOR UPDATE"),
                {"id": index.id},
            )
            if stored != index.model_dump(mode="json"):
                raise ValueError("Index identity mismatch")
            rows = await session.execute(
                text("""
                    SELECT v.id,v.document_id,count(c.id) AS chunks,count(e.chunk_id) AS embedded
                    FROM knowledge_document_versions v
                    LEFT JOIN knowledge_chunks c ON c.version_id=v.id
                    LEFT JOIN knowledge_embeddings e ON e.chunk_id=c.id AND e.index_id=:index
                    WHERE v.id=ANY(:versions)
                    GROUP BY v.id,v.document_id
                """),
                {"versions": versions, "index": index.id},
            )
            documents = list(rows.mappings())
            if (
                len(documents) != len(versions)
                or len({row["document_id"] for row in documents}) != len(versions)
                or any(row["chunks"] == 0 or row["chunks"] != row["embedded"] for row in documents)
            ):
                raise ValueError("Incomplete corpus; previous index remains active")
            for row in documents:
                await session.execute(
                    text(
                        "UPDATE knowledge_documents "
                        "SET current_version_id=:version,updated_at=now() "
                        "WHERE id=:document"
                    ),
                    {"version": row["id"], "document": row["document_id"]},
                )
            await session.execute(text("UPDATE knowledge_indexes SET active=false WHERE active"))
            await session.execute(
                text("UPDATE knowledge_indexes SET active=true WHERE id=:id"), {"id": index.id}
            )

    async def store_vector(
        self, chunk_id: UUID, index_id: str, vector: list[float], cache_key: str
    ) -> None:
        validate_vector(vector)
        async with asyncio.timeout(5), self.database.session() as session, session.begin():
            await session.execute(
                text("""
                INSERT INTO knowledge_embeddings(chunk_id,index_id,embedding,cache_key)
                VALUES (:chunk,:index,CAST(:vector AS vector),:cache)
                ON CONFLICT (chunk_id,index_id) DO NOTHING
            """),
                {
                    "chunk": chunk_id,
                    "index": index_id,
                    "vector": json.dumps(vector),
                    "cache": cache_key,
                },
            )

    async def candidates(
        self,
        scope: VehicleScope,
        query: str,
        index_id: str,
        vector: list[float] | None,
        topic: str,
        source_tuner: str | None = None,
    ) -> list[dict[str, Any]]:
        if vector is not None:
            validate_vector(vector)
        # Only verified non-community current sources enter candidate generation. The latest
        # verification snapshot may revoke an old source without mutating historical citations.
        sql = """
            WITH eligible AS MATERIALIZED (
                SELECT c.id,c.snapshot AS chunk,v.snapshot AS document,s.snapshot AS source,
                  ts_rank_cd(c.lexical,to_tsquery('simple',:lexical)) AS lexical_score,
                  CASE WHEN CAST(:vector AS vector) IS NOT NULL AND e.embedding IS NOT NULL
                    THEN 1 - (e.embedding <=> CAST(:vector AS vector)) ELSE NULL END AS vector_score
                FROM knowledge_chunks c
                JOIN knowledge_document_versions v ON v.id=c.version_id
                JOIN knowledge_documents d ON d.current_version_id=v.id
                JOIN knowledge_sources s ON s.id=v.source_id AND s.version=v.source_version
                JOIN LATERAL (SELECT snapshot FROM knowledge_sources latest
                    WHERE latest.id=s.id ORDER BY latest.version DESC LIMIT 1)
                    current_source ON true
                JOIN knowledge_embeddings e ON e.chunk_id=c.id AND e.index_id=:index
                WHERE current_source.snapshot->>'status'='VERIFIED'
                  AND (v.snapshot->'applicability'->'subsystems') ? :topic
                  AND (CAST(:source_tuner AS text) IS NULL OR
                       lower(v.snapshot->'applicability'->>'tuner')=
                       lower(CAST(:source_tuner AS text)))
                  AND s.snapshot->>'status'='VERIFIED'
                  AND s.snapshot->>'trust' IN ('TIER_1_AUTHORITATIVE','TIER_2_STRONG_TECHNICAL',
                                               'TIER_3_CURATED_INTERNAL')
                  AND v.snapshot->>'status' IN ('EXTRACTED','INDEXED')
                  AND (v.snapshot->'applicability'->>'engine' IS NULL OR
                       lower(v.snapshot->'applicability'->>'engine')=lower(:engine))
                  AND (v.snapshot->'applicability'->>'platform' IS NULL OR
                       lower(v.snapshot->'applicability'->>'platform')=lower(:platform))
            ), selected AS (
                (SELECT id FROM eligible WHERE lexical_score>0
                 ORDER BY lexical_score DESC,id LIMIT 30)
                UNION
                (SELECT id FROM eligible WHERE vector_score>0.2
                 ORDER BY vector_score DESC,id LIMIT 30)
            ) SELECT eligible.* FROM eligible JOIN selected USING(id)
        """
        async with asyncio.timeout(5), self.database.session() as session:
            rows = await session.execute(
                text(sql),
                {
                    "lexical": " | ".join(
                        list(dict.fromkeys(re.findall(r"[a-z0-9]+", query.lower())))[:40]
                    ),
                    "topic": topic,
                    "source_tuner": source_tuner,
                    "index": index_id,
                    "engine": scope.engine,
                    "platform": scope.platform,
                    "vector": json.dumps(vector) if vector is not None else None,
                },
            )
            return [dict(row) for row in rows.mappings()]

    async def retrieval_revision(self) -> str:
        """Invalidate retrieval cache on publication, source revocation or conflict review."""
        async with asyncio.timeout(5), self.database.session() as session:
            revision = await session.scalar(
                text("""
                    SELECT md5(concat_ws('|',
                        (SELECT string_agg(id::text||':'||version::text,',' ORDER BY id,version)
                         FROM knowledge_sources),
                        (SELECT string_agg(id::text||':'||current_version_id::text,',' ORDER BY id)
                         FROM knowledge_documents),
                        (SELECT string_agg(id::text||':'||status,',' ORDER BY id)
                         FROM knowledge_conflicts),
                        (SELECT string_agg(id,',' ORDER BY id) FROM knowledge_indexes WHERE active)
                    ))
                """)
            )
            return str(revision)

    async def conflicts(self, versions: list[UUID], topic: str) -> list[dict[str, Any]]:
        async with asyncio.timeout(5), self.database.session() as session:
            rows = await session.execute(
                text("""
                SELECT id,left_version_id,right_version_id,topic,status,explanation
                FROM knowledge_conflicts
                WHERE status='OPEN' AND topic=:topic AND
                  (left_version_id=ANY(:versions) OR right_version_id=ANY(:versions)) LIMIT 16
            """),
                {"topic": topic, "versions": versions},
            )
            return [dict(row) for row in rows.mappings()]

    async def record_conflict(self, conflict: SourceConflict) -> None:
        async with asyncio.timeout(5), self.database.session() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:id))"), {"id": str(conflict.id)}
            )
            existing = (
                (
                    await session.execute(
                        text(
                            "SELECT id,left_version_id,right_version_id,topic,status,explanation "
                            "FROM knowledge_conflicts WHERE id=:id"
                        ),
                        {"id": conflict.id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None and SourceConflict.model_validate(dict(existing)) != conflict:
                raise ValueError("Conflict records are immutable; create a reviewed new record")
            await session.execute(
                text(
                    "INSERT INTO knowledge_conflicts "
                    "(id,left_version_id,right_version_id,topic,status,explanation) "
                    "VALUES (:id,:left_version_id,:right_version_id,:topic,:status,:explanation) "
                    "ON CONFLICT DO NOTHING"
                ),
                conflict.model_dump(),
            )

    async def audit(self, result: RetrievalResult) -> None:
        from vehicle_platform.knowledge.domain import scope_hash

        async with asyncio.timeout(5), self.database.session() as session, session.begin():
            await session.execute(
                text("""
                INSERT INTO knowledge_retrieval_runs(id,vehicle_id,index_id,scope_hash,snapshot)
                VALUES (:id,:vehicle,:index,:scope,CAST(:snapshot AS jsonb))
            """),
                {
                    "id": result.id,
                    "vehicle": result.scope.vehicle_id,
                    "index": result.index_id,
                    "scope": scope_hash(result.scope),
                    "snapshot": result.model_dump_json(),
                },
            )

    async def catalog(self) -> dict[str, Any]:
        async with asyncio.timeout(5), self.database.session() as session:
            sources = await session.scalars(
                text("""
                SELECT DISTINCT ON (id) snapshot FROM knowledge_sources
                ORDER BY id,version DESC LIMIT 100
            """)
            )
            documents = await session.scalars(
                text("""
                SELECT v.snapshot FROM knowledge_document_versions v
                JOIN knowledge_documents d ON d.current_version_id=v.id ORDER BY v.id LIMIT 100
            """)
            )
            indexes = await session.execute(
                text("SELECT snapshot,active FROM knowledge_indexes ORDER BY id LIMIT 20")
            )
            counts = await session.execute(
                text("""
                SELECT (SELECT count(*) FROM knowledge_chunks) AS chunks,
                       (SELECT count(*) FROM knowledge_embeddings) AS embeddings
            """)
            )
            return {
                "sources": list(sources),
                "documents": list(documents),
                "indexes": [dict(row) for row in indexes.mappings()],
                **dict(counts.mappings().one()),
            }

    async def get_retrieval(self, vehicle_id: UUID, retrieval_id: UUID) -> RetrievalResult | None:
        async with asyncio.timeout(5), self.database.session() as session:
            result = await session.scalar(
                text(
                    "SELECT snapshot FROM knowledge_retrieval_runs "
                    "WHERE id=:id AND vehicle_id=:vehicle"
                ),
                {"id": retrieval_id, "vehicle": vehicle_id},
            )
            return RetrievalResult.model_validate(result) if result else None
