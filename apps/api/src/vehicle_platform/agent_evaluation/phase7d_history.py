"""Integrity-checked compatibility view of the immutable Phase 7D suite."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from vehicle_platform.evaluation.phase7d import Suite

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_MAPPING = ROOT / "evals/phase11/phase7d-id-mapping-v1.json"
DEFAULT_SUITE = ROOT / "evals/phase7d/suite-v2.json"


class Phase7DHistoryError(ValueError):
    """The historical mapping or its immutable source suite is invalid."""


def load_phase7d_history(
    mapping_path: Path = DEFAULT_MAPPING,
    suite_path: Path = DEFAULT_SUITE,
) -> dict[str, Any]:
    """Load and cross-check all 120 scheduled legacy slots against suite v2."""
    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        suite_bytes = suite_path.read_bytes()
        suite = Suite.model_validate_json(suite_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise Phase7DHistoryError("phase7d_history_unreadable") from exc
    if not isinstance(mapping, dict) or set(mapping) != {
        "schema_version",
        "mapping_version",
        "source_suite",
        "source_suite_sha256",
        "case_mappings",
        "historical_observations",
        "comparison_policy",
    }:
        raise Phase7DHistoryError("phase7d_mapping_shape_invalid")
    source_sha = sha256(suite_bytes).hexdigest()
    if (
        mapping["schema_version"] != "1.0"
        or mapping["mapping_version"] != "phase7d-id-map-v1"
        or mapping["source_suite"] != "evals/phase7d/suite-v2.json"
        or suite.version != "phase7d-v2"
        or mapping["source_suite_sha256"] != source_sha
    ):
        raise Phase7DHistoryError("phase7d_source_identity_mismatch")

    expected: dict[str, dict[str, Any]] = {}
    for case in suite.cases:
        expected[case.case_id] = {
            "legacy_case_id": case.case_id,
            "category": case.category,
            "critical": case.critical,
            "scheduled_repeats": [0, 1, 2] if case.critical else [0],
            "phase11_case_id": "P11-BENIGN-001" if case.case_id == "A01" else None,
            "relationship": "similar_intent_not_equivalent"
            if case.case_id == "A01"
            else "legacy_identity_preserved",
        }
    rows = mapping["case_mappings"]
    if not isinstance(rows, list) or rows != [expected[case.case_id] for case in suite.cases]:
        raise Phase7DHistoryError("phase7d_case_mapping_mismatch")

    schedule = suite.schedule()
    observations = mapping["historical_observations"]
    expected_round15 = {
        "PASS": 93,
        "SEMANTIC_FAILURE": 10,
        "RUNTIME_FAILURE": 9,
        "PROVIDER_FAILURE": 6,
        "INTERRUPTED": 1,
        "SKIPPED_BUDGET_LIMIT": 1,
    }
    if (
        len(schedule) != 120
        or not isinstance(observations, dict)
        or observations.get("scheduled_slots") != 120
        or observations.get("unique_questions") != 80
        or observations.get("latest_pass_slots_across_rounds") != 120
        or observations.get("latest_observation_rounds") != [15, 16, 17, 22]
        or observations.get("latest_pass_observations_by_round")
        != {"15": 93, "16": 24, "17": 2, "22": 1}
        or observations.get("latest_g03_real_round")
        != {"round": 22, "repository_sha": "b459c14626d04a1e829ae8b7dc3476311f6a470b"}
        or observations.get("uniform_final_source_cohort") is not False
        or observations.get("accumulated_estimated_spend_usd") != 4.326918555
        or observations.get("authorized_budget_usd") != 5.0
        or observations.get("unknown_usage_reservations") != 67
        or observations.get("remaining_budget_usd") != 0.673081445
        or observations.get("native_round_15")
        != {"round": 15, "slot_count": 120, "outcomes": expected_round15}
    ):
        raise Phase7DHistoryError("phase7d_historical_baseline_mismatch")
    if (
        mapping["comparison_policy"]
        != "Keep Phase 7D history separate; never combine rounds or infer final-source reliability."
    ):
        raise Phase7DHistoryError("phase7d_comparison_policy_invalid")
    return mapping
