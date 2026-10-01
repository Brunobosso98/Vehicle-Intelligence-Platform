"""Enable the required extension, without creating telemetry tables.

Downgrade intentionally preserves the extension: dropping it could delete future
hypertables. Only the Alembic revision is rolled back. See migration runbook.
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")


def downgrade() -> None:
    pass
