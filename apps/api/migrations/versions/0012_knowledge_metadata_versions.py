"""Permit immutable metadata revisions of an unchanged documentary selection.

The document-version UUID identifies the complete reviewed snapshot. Its text checksum
remains a reusable embedding identity and must not prohibit an applicability correction.
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

CONSTRAINT = "knowledge_document_versions_document_id_checksum_key"


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.drop_constraint(CONSTRAINT, "knowledge_document_versions", type_="unique")
    op.create_index(
        "knowledge_document_content_lookup",
        "knowledge_document_versions",
        ["document_id", "checksum"],
    )


def downgrade() -> None:
    # PostgreSQL refuses restoration if metadata revisions share a content checksum.
    # Do not delete history to make rollback possible; the transaction stays at 0012.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_unique_constraint(
        CONSTRAINT, "knowledge_document_versions", ["document_id", "checksum"]
    )
    op.drop_index("knowledge_document_content_lookup", table_name="knowledge_document_versions")
