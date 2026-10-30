from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from vehicle_platform.features.domain import stable_hash
from vehicle_platform.ml.domain import SupervisedRow


class EvaluationSplitError(ValueError):
    pass


@dataclass(frozen=True)
class EvaluationPartitions:
    calibration: tuple[SupervisedRow, ...]
    validation: tuple[SupervisedRow, ...]
    test: tuple[SupervisedRow, ...]
    groups: dict[str, tuple[str, ...]]
    cutoffs: dict[str, str]
    row_fingerprints: dict[str, str]
    group_fingerprints: dict[str, str]


def chronological_calibration_split(
    rows: tuple[SupervisedRow, ...],
    *,
    calibration_fraction: float = 1 / 3,
    validation_fraction: float = 1 / 3,
) -> EvaluationPartitions:
    if not rows:
        raise EvaluationSplitError("evaluation dataset is empty")
    if not 0.30 <= calibration_fraction <= 0.70 or not 0.10 <= validation_fraction <= 0.40:
        raise EvaluationSplitError("split fractions exceed fixed research bounds")
    if calibration_fraction + validation_fraction >= 0.90:
        raise EvaluationSplitError("test fraction must retain at least ten percent")
    row_ids = [row.row_id for row in rows]
    if len(set(row_ids)) != len(row_ids):
        raise EvaluationSplitError("duplicate physical example identity in evaluation dataset")
    grouped: dict[str, list[SupervisedRow]] = defaultdict(list)
    for row in rows:
        if row.group_id != row.session_id:
            raise EvaluationSplitError("evaluation grouping must use independent sessions")
        grouped[row.group_id].append(row)
    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: (
            min(row.input_started_at for row in item[1]),
            max(row.target_started_at for row in item[1]),
            item[0],
        ),
    )
    if len(ordered_groups) < 10:
        raise EvaluationSplitError("chronological evaluation needs at least ten sessions")
    calibration_count = max(1, int(len(ordered_groups) * calibration_fraction))
    validation_count = max(1, int(len(ordered_groups) * validation_fraction))
    # The fixed 10-session and fraction bounds guarantee a held-out group.
    if calibration_count + validation_count >= len(ordered_groups):  # pragma: no branch
        calibration_count = len(ordered_groups) - validation_count - 1
    calibration_groups = ordered_groups[:calibration_count]
    validation_groups = ordered_groups[calibration_count : calibration_count + validation_count]
    test_groups = ordered_groups[calibration_count + validation_count :]
    # The same bounds guarantee every chronological slice is nonempty.
    if (
        min(len(calibration_groups), len(validation_groups), len(test_groups)) == 0
    ):  # pragma: no branch
        raise EvaluationSplitError("calibration, validation and test must all be nonempty")
    partitions_by_name = {
        "calibration": calibration_groups,
        "validation": validation_groups,
        "test": test_groups,
    }
    partitions = {
        name: tuple(row for _, members in group_rows for row in members)
        for name, group_rows in partitions_by_name.items()
    }
    _assert_partition_safety(partitions)
    for axis in ("vehicle_id", "configuration_id"):
        seen: set[str] = set()
        for name in ("calibration", "validation", "test"):
            identities = {getattr(row, axis) for row in partitions[name]}
            if seen.intersection(identities):
                raise EvaluationSplitError(
                    f"evaluation {axis} holdouts overlap across chronological partitions"
                )
            seen.update(identities)
    cutoffs: dict[str, str] = {}
    row_fingerprints: dict[str, str] = {}
    group_fingerprints: dict[str, str] = {}
    groups: dict[str, tuple[str, ...]] = {}
    previous_end: datetime | None = None
    for name, group_rows in partitions_by_name.items():
        partition_rows = partitions[name]
        start = min(row.input_started_at for row in partition_rows)
        end = max(row.target_started_at for row in partition_rows)
        if previous_end is not None and previous_end >= start:
            raise EvaluationSplitError("chronological partitions overlap in observed time")
        previous_end = end
        cutoffs[f"{name}_start"] = start.isoformat()
        cutoffs[f"{name}_end"] = end.isoformat()
        groups[name] = tuple(sorted(group_id for group_id, _ in group_rows))
        row_fingerprints[name] = stable_hash(sorted(row.row_id for row in partition_rows))
        group_fingerprints[name] = stable_hash(groups[name])
    return EvaluationPartitions(
        calibration=partitions["calibration"],
        validation=partitions["validation"],
        test=partitions["test"],
        groups=groups,
        cutoffs=cutoffs,
        row_fingerprints=row_fingerprints,
        group_fingerprints=group_fingerprints,
    )


def assert_disjoint_training_source(
    training_rows: tuple[SupervisedRow, ...], partitions: EvaluationPartitions
) -> None:
    training_groups = {row.group_id for row in training_rows}
    training_vehicles = {row.vehicle_id for row in training_rows}
    training_configurations = {row.configuration_id for row in training_rows}
    training_pulls = {
        pull_id for row in training_rows for pull_id in (row.input_pull_id, row.target_pull_id)
    }
    if not training_rows:
        raise EvaluationSplitError("frozen model training source is empty")
    for name, partition_rows in (
        ("calibration", partitions.calibration),
        ("validation", partitions.validation),
        ("test", partitions.test),
    ):
        if training_groups.intersection(row.group_id for row in partition_rows):
            raise EvaluationSplitError(f"model training sessions overlap {name} sessions")
        if training_vehicles.intersection(row.vehicle_id for row in partition_rows):
            raise EvaluationSplitError(f"model training vehicles overlap {name} vehicles")
        if training_configurations.intersection(row.configuration_id for row in partition_rows):
            raise EvaluationSplitError(
                f"model training configurations overlap {name} configurations"
            )
        evaluation_pulls = {
            pull_id for row in partition_rows for pull_id in (row.input_pull_id, row.target_pull_id)
        }
        if training_pulls.intersection(evaluation_pulls):
            raise EvaluationSplitError(
                f"a physical pull is reused between model training and {name}"
            )
        if max(row.target_started_at for row in training_rows) >= min(
            row.input_started_at for row in partition_rows
        ):
            raise EvaluationSplitError(
                f"{name} observations are not strictly later than model training"
            )


def _assert_partition_safety(partitions: dict[str, tuple[SupervisedRow, ...]]) -> None:
    seen_sessions: set[str] = set()
    seen_pulls: set[str] = set()
    for name in ("calibration", "validation", "test"):
        rows = partitions[name]
        session_ids = {row.group_id for row in rows}
        # Groups were keyed by session and sliced disjointly above.
        if seen_sessions.intersection(session_ids):  # pragma: no branch
            raise EvaluationSplitError("one session appears in multiple evaluation partitions")
        seen_sessions.update(session_ids)
        pull_ids = {pull_id for row in rows for pull_id in (row.input_pull_id, row.target_pull_id)}
        if seen_pulls.intersection(pull_ids):
            raise EvaluationSplitError(
                "one physical pull appears in multiple evaluation partitions"
            )
        seen_pulls.update(pull_ids)
        for row in rows:
            if row.input_available_at >= row.target_started_at:
                raise EvaluationSplitError("post-cutoff feature or target leakage was detected")


def fold_summary(
    partition: str,
    rows: tuple[SupervisedRow, ...],
    *,
    row_fingerprint: str,
    session_fingerprint: str,
    source_fingerprint: str,
    eligible: bool,
    exclusions: dict[str, int] | None = None,
) -> dict[str, Any]:
    from vehicle_platform.evaluation.contracts import FoldManifest

    return FoldManifest(
        fold_id=f"phase9g-{partition.lower()}-v1",
        partition=partition,
        row_count=len(rows),
        positive_count=sum(row.target for row in rows),
        negative_count=sum(not row.target for row in rows),
        session_count=len({row.group_id for row in rows}),
        vehicle_count=len({row.vehicle_id for row in rows}),
        start_at=min((row.input_started_at for row in rows), default=None),
        end_at=max((row.target_started_at for row in rows), default=None),
        row_fingerprint=row_fingerprint,
        session_fingerprint=session_fingerprint,
        source_fingerprint=source_fingerprint,
        eligible=eligible,
        exclusions=exclusions or {},
    ).model_dump(mode="json")
