# Migration review

Use `make test-integration`. Test a fresh database, the previous revision, rerun at head,
and a safe downgrade/re-upgrade. Assess lock duration and deployed application compatibility.
Foundation downgrade preserves TimescaleDB deliberately: DROP EXTENSION could destroy future data.
Document irreversible operations and recovery before applying them. Tests never target the app database.
