---
name: database-migration
description: Add or review a schema migration and its rollout; not for ordinary database reads.
---

# database-migration

Review schema history, backward/forward compatibility, locks, data risk and rollback.
Create a new Alembic revision; do not rewrite an applied revision.
Test upgrade from clean and prior schema, and downgrade where safe, using disposable databases.
Never use production data. See [Migration review](references/migrations.md).
