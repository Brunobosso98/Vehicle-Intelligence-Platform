---
type: "query"
date: "2026-11-22T02:20:00.949831+00:00"
question: "How should Phase 10 verify source roles for immutable anomaly evaluation pulls?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["Pull", "DatasetBinding", "SourceRole"]
---

# Q: How should Phase 10 verify source roles for immutable anomaly evaluation pulls?

## Answer

Expanded from original query via vocab: [artifact, dataset, lineage, mlops, pull, role, schema, source, evaluation]. The Phase 9A schema stores source_type on driving_sessions; pulls reference their owning session through session_id. The independent checker joins pulls p to driving_sessions s on s.id=p.session_id, then verifies s.source_type and pull timestamps. Evidence: apps/api/migrations/versions/0002_vehicle_telemetry_core.py, apps/api/migrations/versions/0003_session_pull_detection.py, and scripts/check_mlops.py.

## Outcome

- Signal: useful

## Source Nodes

- Pull
- DatasetBinding
- SourceRole