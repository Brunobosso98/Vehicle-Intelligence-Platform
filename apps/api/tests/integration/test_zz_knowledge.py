"""Additive knowledge migration lifecycle over the same disposable Timescale database."""

import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration
API = Path(__file__).resolve().parents[2]


async def test_knowledge_upgrade_downgrade_reupgrade_preserves_vehicle_rows() -> None:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        pytest.fail("Knowledge migration requires disposable vehicle_test* database")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            original = await connection.scalar(text("SELECT count(*) FROM vehicles"))
        for command, target in (("downgrade", "0010"), ("upgrade", "head"), ("upgrade", "head")):
            child = await asyncio.create_subprocess_exec(
                str(API / ".venv/bin/alembic"),
                command,
                target,
                cwd=API,
                env=os.environ | {"DATABASE_URL": url},
            )
            async with asyncio.timeout(60):
                assert await child.wait() == 0
            async with engine.connect() as connection:
                assert await connection.scalar(text("SELECT count(*) FROM vehicles")) == original
                assert (
                    await connection.scalar(
                        text("SELECT extversion FROM pg_extension WHERE extname='vector'")
                    )
                    == "0.8.2"
                )
                table = await connection.scalar(text("SELECT to_regclass('knowledge_chunks')"))
                assert (table is None) == (command == "downgrade")
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM timescaledb_information.hypertables "
                            "WHERE hypertable_name='telemetry_samples'"
                        )
                    )
                    == 1
                )
    finally:
        await engine.dispose()


async def test_partial_corpus_does_not_replace_published_index() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from vehicle_platform.core.config import Settings
    from vehicle_platform.infrastructure.database import Database
    from vehicle_platform.knowledge.domain import (
        Applicability,
        DocumentVersion,
        KnowledgeIndexVersion,
        KnowledgeSource,
        SourceStatus,
        Trust,
        digest,
    )
    from vehicle_platform.knowledge.extraction import Section, chunks
    from vehicle_platform.knowledge.repository import KnowledgeRepository
    from vehicle_platform.observability.telemetry import Telemetry

    url = os.environ["TEST_DATABASE_URL"]
    assert url.rsplit("/", 1)[-1].startswith("vehicle_test")
    config = Settings(database_url=url, environment="test")
    database = Database(config)
    telemetry = Telemetry(config)
    repo = KnowledgeRepository(database, telemetry)
    now = datetime.now(UTC)
    source = KnowledgeSource(
        id=uuid4(),
        publisher="Project-authored synthetic integration fixture",
        canonical_url="https://example.com/synthetic-index-activation",
        source_type="oem_training",
        trust=Trust.TIER_1_AUTHORITATIVE,
        status=SourceStatus.VERIFIED,
        verified_at=now,
    )
    document_id = uuid4()
    previous = None
    previous_doc = None
    try:
        for label in ("old", "new", "metadata"):
            content_label = "new" if label == "metadata" else label
            content = f"Synthetic {content_label} N55 fuel pressure control operating reference."
            if label == "metadata":
                source = source.model_copy(update={"version": 2})
            doc = DocumentVersion(
                id=uuid4(),
                document_id=document_id,
                source_id=source.id,
                source_version=source.version,
                title="Synthetic index publication test",
                retrieved_at=now,
                checksum=digest(content),
                mime="text/plain",
                applicability=Applicability(
                    engine="N55",
                    subsystems=["fuel"],
                    hardware=["electronic wastegate"] if label == "metadata" else [],
                ),
                license_note="Project-authored synthetic fixture",
                redistribution="synthetic",
                status="EXTRACTED",
            )
            pieces = chunks(doc.id, [Section(("Synthetic reference",), content)])
            index = KnowledgeIndexVersion(
                id=f"activation-test-{uuid4()}",
                corpus_checksum=digest(content),
                created_at=now,
            )
            await repo.index(index)
            await repo.ingest(source, doc, pieces)
            with pytest.raises(ValueError, match="Incomplete corpus"):
                await repo.activate_corpus(index, [doc.id])
            if previous:
                assert await repo.active_index() == previous
                async with database.session() as session:
                    current = await session.scalar(
                        text("SELECT current_version_id FROM knowledge_documents WHERE id=:id"),
                        {"id": document_id},
                    )
                    assert current == previous_doc
            for piece in pieces:
                await repo.store_vector(
                    piece.id,
                    index.id,
                    [1.0] + [0.0] * 1535,
                    index.cache_key(doc.checksum, piece.checksum),
                )
            await repo.activate_corpus(index, [doc.id])
            assert await repo.active_index() == index
            if label == "metadata":
                async with database.session() as session:
                    snapshots = list(
                        (
                            await session.execute(
                                text(
                                    "SELECT snapshot FROM knowledge_document_versions "
                                    "WHERE document_id=:document AND checksum=:checksum"
                                ),
                                {"document": document_id, "checksum": doc.checksum},
                            )
                        ).scalars()
                    )
                assert {snapshot["source_version"] for snapshot in snapshots} == {1, 2}
                assert len(snapshots) == 2
                child = await asyncio.create_subprocess_exec(
                    str(API / ".venv/bin/alembic"),
                    "downgrade",
                    "0011",
                    cwd=API,
                    env=os.environ | {"DATABASE_URL": url},
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                async with asyncio.timeout(60):
                    assert await child.wait() != 0
                async with database.session() as session:
                    assert (
                        await session.scalar(text("SELECT version_num FROM alembic_version"))
                        == "0012"
                    )
                    assert (
                        await session.scalar(
                            text(
                                "SELECT count(*) FROM knowledge_document_versions "
                                "WHERE document_id=:id"
                            ),
                            {"id": document_id},
                        )
                        == 3
                    )
            previous, previous_doc = index, doc.id
        with pytest.raises(ValueError, match="nonempty unique"):
            await repo.activate_corpus(index, [])
        with pytest.raises(ValueError, match="Source version mismatch"):
            await repo.ingest(source.model_copy(update={"version": 99}), doc, pieces)
        from prometheus_client.parser import text_string_to_metric_families

        values = {
            sample.name: sample.value
            for family in text_string_to_metric_families(telemetry.render_metrics().decode())
            for sample in family.samples
        }
        assert values["knowledge_ingestion_total"] == 3
        assert values["knowledge_chunks_total"] == 3
        assert values["knowledge_ingestion_failures_total"] == 1
    finally:
        await database.close()
        telemetry.shutdown()


async def test_trusted_source_conflict_preserves_conditions_and_invalidates_cache() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from vehicle_platform.core.config import Settings
    from vehicle_platform.infrastructure.database import Database
    from vehicle_platform.knowledge.domain import (
        Applicability,
        DocumentChunk,
        DocumentVersion,
        KnowledgeIndexVersion,
        KnowledgeSource,
        NumericFact,
        RetrievalIntent,
        SourceConflict,
        SourceStatus,
        Trust,
        VehicleScope,
        digest,
    )
    from vehicle_platform.knowledge.extraction import Section, chunks
    from vehicle_platform.knowledge.repository import KnowledgeRepository
    from vehicle_platform.knowledge.retrieval import KnowledgeService, validate_numeric
    from vehicle_platform.observability.telemetry import Telemetry

    url = os.environ["TEST_DATABASE_URL"]
    assert url.rsplit("/", 1)[-1].startswith("vehicle_test")
    settings = Settings(database_url=url, environment="test")
    database, telemetry = Database(settings), Telemetry(settings)
    repo = KnowledgeRepository(database)
    now, versions = datetime.now(UTC), []
    index = KnowledgeIndexVersion(
        id=f"synthetic-conflicts-{uuid4()}",
        corpus_checksum=digest("synthetic conflict fixture"),
        created_at=now,
    )
    vector = [1.0] + [0.0] * 1535
    try:
        await repo.index(index)
        for calibration, pressure, tier in (
            ("stock", 123, Trust.TIER_1_AUTHORITATIVE),
            ("tune_specific", 150, Trust.TIER_2_STRONG_TECHNICAL),
        ):
            conditions = f"synthetic {calibration} operating condition"
            content = f"Synthetic N55 fuel reference: {pressure} bar under {conditions}."
            source = KnowledgeSource(
                id=uuid4(),
                publisher="Project-authored synthetic source",
                canonical_url=f"https://example.com/synthetic/{calibration}",
                source_type="oem_training" if calibration == "stock" else "tuner",
                trust=tier,
                status=SourceStatus.VERIFIED,
                verified_at=now,
            )
            app = Applicability(
                engine="N55",
                subsystems=["fuel"],
                calibration=calibration,
                tuner="Synthetic vendor" if calibration == "tune_specific" else None,
                map_version="fixture-v1" if calibration == "tune_specific" else None,
            )
            doc = DocumentVersion(
                id=uuid4(),
                document_id=uuid4(),
                source_id=source.id,
                source_version=1,
                title="Synthetic conditional reference",
                retrieved_at=now,
                checksum=digest(content),
                mime="text/plain",
                applicability=app,
                license_note="Project-authored synthetic fixture",
                redistribution="synthetic",
                status="EXTRACTED",
            )
            pieces = chunks(doc.id, [Section(("Synthetic fuel conditions",), content)])
            piece = DocumentChunk.model_validate(
                pieces[0].model_dump()
                | {
                    "quality": "reviewed",
                    "numeric_facts": [
                        NumericFact(
                            value=pressure,
                            unit="bar",
                            conditions=conditions,
                            original=f"{pressure} bar",
                            kind="stock_target" if calibration == "stock" else "tune_target",
                            topic="fuel",
                        ).model_dump()
                    ],
                }
            )
            await repo.ingest(source, doc, [piece])
            await repo.store_vector(
                piece.id, index.id, vector, index.cache_key(doc.checksum, piece.checksum)
            )
            versions.append(doc.id)
        await repo.activate_corpus(index, versions)

        async def encode(query, index_id):
            assert index_id == index.id
            return vector

        service = KnowledgeService(repo, telemetry, encode)
        scope = VehicleScope(
            vehicle_id=uuid4(),
            engine="N55",
            calibration="tuned",
            tuner="Synthetic vendor",
            map_version="fixture-v1",
            temporal_valid=True,
            as_of=now,
        )
        intent = RetrievalIntent(
            query="N55 fuel pressure reference", topic="fuel", need="normative_target"
        )
        before = await service.search(intent, scope)
        from vehicle_platform.knowledge.grounding import render, report

        prior_report = report(before, hybrid=True)
        assert len(prior_report.claims) == 1 and prior_report.claims[0].normative
        assert "synthetic tune_specific operating condition" in render(prior_report)
        exact = next(e for e in before.evidence if e.document.id == versions[1])
        assert exact.eligible
        validate_numeric(exact, 150, "bar", "synthetic tune_specific operating condition", scope)
        revision = await repo.retrieval_revision()
        conflict = SourceConflict(
            id=uuid4(),
            left_version_id=versions[0],
            right_version_id=versions[1],
            topic="fuel",
            explanation=(
                "Synthetic trusted references give different values under stock and tuned "
                "conditions; a universal merged target is unsupported."
            ),
        )
        await repo.record_conflict(conflict)
        await repo.record_conflict(conflict)
        assert await repo.retrieval_revision() != revision
        after = await service.search(intent, scope)
        assert {e.document.id for e in after.evidence} == set(versions)
        assert after.source_conflicts == [conflict]
        assert "unresolved_source_conflict" in after.knowledge_gaps
        assert not any(e.eligible for e in after.evidence)
        assert not report(after, hybrid=True).claims
        assert {f.value for e in after.evidence for f in e.numeric_facts} == {123.0, 150.0}
        assert {e.applicability.status for e in after.evidence} == {"APPLICABLE", "PARTIAL"}
        with pytest.raises(ValueError, match="Ineligible"):
            validate_numeric(
                after.evidence[0], 150, "bar", "synthetic tune_specific operating condition", scope
            )
        with pytest.raises(ValueError, match="immutable"):
            await repo.record_conflict(
                conflict.model_copy(update={"explanation": "Mutated unreviewed conflict"})
            )
        stored = await repo.get_retrieval(scope.vehicle_id, after.id)
        assert stored and stored.source_conflicts == [conflict]
    finally:
        await database.close()
        telemetry.shutdown()
