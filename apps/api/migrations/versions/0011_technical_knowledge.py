"""Add immutable technical sources, corpus versions, pgvector and retrieval audit.

No prior domain rows are rewritten. Downgrade removes only knowledge-owned tables;
the shared vector extension is preserved. Exact cosine search suits the bounded initial corpus.
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        CREATE TABLE knowledge_sources (
            id uuid NOT NULL, version integer NOT NULL CHECK (version > 0),
            snapshot jsonb NOT NULL CHECK (octet_length(snapshot::text) <= 8192),
            created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (id, version)
        )
    """)
    op.execute("""
        CREATE TABLE knowledge_documents (
            id uuid PRIMARY KEY, source_id uuid NOT NULL, current_version_id uuid,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE knowledge_document_versions (
            id uuid PRIMARY KEY, document_id uuid NOT NULL REFERENCES knowledge_documents(id),
            source_id uuid NOT NULL, source_version integer NOT NULL,
            checksum varchar(64) NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
            snapshot jsonb NOT NULL CHECK (octet_length(snapshot::text) <= 16384),
            FOREIGN KEY (source_id, source_version) REFERENCES knowledge_sources(id, version),
            UNIQUE (document_id, checksum)
        )
    """)
    op.execute("""
        ALTER TABLE knowledge_documents ADD CONSTRAINT fk_knowledge_current_version
        FOREIGN KEY (current_version_id) REFERENCES knowledge_document_versions(id)
    """)
    op.execute("""
        CREATE TABLE knowledge_indexes (
            id varchar(160) PRIMARY KEY,
            snapshot jsonb NOT NULL CHECK (octet_length(snapshot::text) <= 8192),
            active boolean NOT NULL DEFAULT false
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX knowledge_one_active_index ON knowledge_indexes(active) WHERE active"
    )
    op.execute("""
        CREATE TABLE knowledge_chunks (
            id uuid PRIMARY KEY,
            version_id uuid NOT NULL REFERENCES knowledge_document_versions(id),
            ordinal integer NOT NULL CHECK (ordinal >= 0),
            checksum varchar(64) NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
            snapshot jsonb NOT NULL CHECK (octet_length(snapshot::text) <= 65536),
            search_text text NOT NULL CHECK (octet_length(search_text) <= 16000),
            lexical tsvector GENERATED ALWAYS AS (to_tsvector('simple', search_text)) STORED,
            UNIQUE(version_id, ordinal)
        )
    """)
    op.execute("CREATE INDEX knowledge_lexical_gin ON knowledge_chunks USING gin(lexical)")
    op.execute("""
        CREATE TABLE knowledge_embeddings (
            chunk_id uuid NOT NULL REFERENCES knowledge_chunks(id),
            index_id varchar(160) NOT NULL REFERENCES knowledge_indexes(id),
            embedding vector(1536) NOT NULL, cache_key varchar(64) NOT NULL,
            PRIMARY KEY(chunk_id, index_id)
        )
    """)
    op.execute("""
        CREATE TABLE knowledge_conflicts (
            id uuid PRIMARY KEY,
            left_version_id uuid NOT NULL REFERENCES knowledge_document_versions(id),
            right_version_id uuid NOT NULL REFERENCES knowledge_document_versions(id),
            topic varchar(80) NOT NULL, status varchar(16) NOT NULL CHECK (status IN ('OPEN','RESOLVED')),
            explanation varchar(1000) NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE knowledge_retrieval_runs (
            id uuid PRIMARY KEY, vehicle_id uuid NOT NULL,
            index_id varchar(160) NOT NULL REFERENCES knowledge_indexes(id),
            scope_hash varchar(64) NOT NULL,
            snapshot jsonb NOT NULL CHECK (octet_length(snapshot::text) <= 131072),
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX knowledge_retrieval_vehicle ON knowledge_retrieval_runs(vehicle_id, created_at DESC)"
    )


def downgrade() -> None:
    for table in (
        "knowledge_retrieval_runs",
        "knowledge_conflicts",
        "knowledge_embeddings",
        "knowledge_chunks",
        "knowledge_indexes",
    ):
        op.drop_table(table)
    op.drop_constraint("fk_knowledge_current_version", "knowledge_documents", type_="foreignkey")
    op.drop_table("knowledge_document_versions")
    op.drop_table("knowledge_documents")
    op.drop_table("knowledge_sources")
