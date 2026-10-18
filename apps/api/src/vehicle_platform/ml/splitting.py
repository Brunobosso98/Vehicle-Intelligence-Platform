from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from vehicle_platform.ml.domain import SupervisedDataset, SupervisedRow, TemporalSplit


class SplitValidationError(ValueError):
    pass


@dataclass(frozen=True)
class TemporalBlock:
    group_ids: tuple[str, ...]
    rows: tuple[SupervisedRow, ...]
    start: datetime
    end: datetime


@dataclass(frozen=True)
class WalkForwardFold:
    index: int
    train: tuple[SupervisedRow, ...]
    validation: tuple[SupervisedRow, ...]
    test: tuple[SupervisedRow, ...]
    train_end: datetime
    validation_end: datetime
    test_end: datetime


def temporal_blocks(rows: tuple[SupervisedRow, ...]) -> tuple[TemporalBlock, ...]:
    grouped: dict[str, list[SupervisedRow]] = defaultdict(list)
    for row in rows:
        grouped[row.group_id].append(row)
    intervals: list[tuple[datetime, datetime, str, tuple[SupervisedRow, ...]]] = []
    for group_id, group_members in grouped.items():
        ordered = tuple(
            sorted(group_members, key=lambda item: (item.target_started_at, item.row_id))
        )
        intervals.append(
            (
                min(item.input_started_at for item in ordered),
                max(item.target_started_at for item in ordered),
                group_id,
                ordered,
            )
        )
    intervals.sort(key=lambda item: (item[0], item[1], item[2]))
    blocks: list[TemporalBlock] = []
    block_start: datetime | None = None
    block_end: datetime | None = None
    block_groups: list[str] = []
    block_rows: list[SupervisedRow] = []
    for start, end, group_id, ordered_rows in intervals:
        if block_start is not None and block_end is not None and start > block_end:
            blocks.append(
                TemporalBlock(
                    tuple(sorted(block_groups)),
                    tuple(
                        sorted(block_rows, key=lambda item: (item.target_started_at, item.row_id))
                    ),
                    block_start,
                    block_end,
                )
            )
            block_start = None
            block_end = None
            block_groups = []
            block_rows = []
        block_start = start if block_start is None else min(block_start, start)
        block_end = end if block_end is None else max(block_end, end)
        block_groups.append(group_id)
        block_rows.extend(ordered_rows)
    if block_start is not None and block_end is not None:
        blocks.append(
            TemporalBlock(
                tuple(sorted(block_groups)),
                tuple(sorted(block_rows, key=lambda item: (item.target_started_at, item.row_id))),
                block_start,
                block_end,
            )
        )
    return tuple(blocks)


def chronological_group_split(dataset: SupervisedDataset) -> TemporalSplit:
    blocks = temporal_blocks(dataset.rows)
    if len(blocks) < 3:
        raise SplitValidationError(
            "INSUFFICIENT_CHRONOLOGICAL_GROUPS: at least three nonoverlapping "
            "session blocks are required"
        )
    train_block_count = max(1, int(len(blocks) * 0.60 + 0.5))
    validation_block_count = max(1, int(len(blocks) * 0.20 + 0.5))
    if train_block_count + validation_block_count >= len(blocks):
        train_block_count = len(blocks) - 2
        validation_block_count = 1
    train_blocks = blocks[:train_block_count]
    validation_blocks = blocks[train_block_count : train_block_count + validation_block_count]
    test_blocks = blocks[train_block_count + validation_block_count :]
    train = tuple(row for block in train_blocks for row in block.rows)
    validation = tuple(row for block in validation_blocks for row in block.rows)
    test = tuple(row for block in test_blocks for row in block.rows)
    _assert_disjoint_groups(train, validation, test)
    if not train or not validation or not test:
        raise SplitValidationError("chronological split produced an empty partition")
    if max(item.target_started_at for item in train) >= min(
        item.input_started_at for item in validation
    ):
        raise SplitValidationError("training and validation temporal blocks overlap")
    if max(item.target_started_at for item in validation) >= min(
        item.input_started_at for item in test
    ):
        raise SplitValidationError("validation and test temporal blocks overlap")
    return _split_result(train, validation, test)


def walk_forward_splits(
    dataset: SupervisedDataset, *, maximum_folds: int = 3
) -> tuple[WalkForwardFold, ...]:
    if maximum_folds < 1 or maximum_folds > 10:
        raise ValueError("walk-forward fold count must be between one and ten")
    blocks = temporal_blocks(dataset.rows)
    folds: list[WalkForwardFold] = []
    first_train_size = max(2, len(blocks) - maximum_folds - 1)
    for offset in range(maximum_folds):
        train_end_index = first_train_size + offset
        validation_index = train_end_index
        test_index = validation_index + 1
        if test_index >= len(blocks):
            break
        train = tuple(row for block in blocks[:train_end_index] for row in block.rows)
        validation = blocks[validation_index].rows
        test = blocks[test_index].rows
        if not train or not validation or not test:
            continue
        train_end = max(item.target_started_at for item in train)
        validation_end = max(item.target_started_at for item in validation)
        test_end = max(item.target_started_at for item in test)
        if train_end >= min(item.input_started_at for item in validation):
            raise SplitValidationError("walk-forward train/validation windows overlap")
        if validation_end >= min(item.input_started_at for item in test):
            raise SplitValidationError("walk-forward validation/test windows overlap")
        folds.append(
            WalkForwardFold(
                len(folds) + 1,
                train,
                validation,
                test,
                train_end,
                validation_end,
                test_end,
            )
        )
    return tuple(folds)


def scenario_holdout_split(dataset: SupervisedDataset, *, held_out_family: str) -> TemporalSplit:
    held = tuple(row for row in dataset.rows if row.scenario_family == held_out_family)
    known = tuple(row for row in dataset.rows if row.scenario_family != held_out_family)
    if not held or not known:
        raise SplitValidationError("scenario holdout requires known and reserved scenario rows")
    known_dataset = _replace_rows(dataset, known)
    known_split = chronological_group_split(known_dataset)
    train, validation, test = known_split.train, known_split.validation, held
    _assert_disjoint_groups(train, validation, test)
    if (
        train
        and held
        and max(item.target_started_at for item in train)
        >= min(item.input_started_at for item in held)
    ):
        raise SplitValidationError("reserved scenario is not strictly later than training data")
    if (
        validation
        and held
        and max(item.target_started_at for item in validation)
        >= min(item.input_started_at for item in held)
    ):
        raise SplitValidationError("reserved scenario is not strictly later than validation data")
    return _split_result(train, validation, test)


def _replace_rows(dataset: SupervisedDataset, rows: tuple[SupervisedRow, ...]) -> SupervisedDataset:
    return SupervisedDataset(
        dataset.task,
        dataset.model_spec,
        dataset.input_dataset_checksum,
        dataset.outcome_dataset_checksum,
        dataset.checksum,
        dataset.source_fingerprint,
        rows,
        dataset.exclusions,
        dataset.manifest,
    )


def _assert_disjoint_groups(*partitions: tuple[SupervisedRow, ...]) -> None:
    seen: set[str] = set()
    for rows in partitions:
        group_ids = {row.group_id for row in rows}
        if seen.intersection(group_ids):
            raise SplitValidationError("a session sequence crosses a split boundary")
        seen.update(group_ids)


def _split_result(
    train: tuple[SupervisedRow, ...],
    validation: tuple[SupervisedRow, ...],
    test: tuple[SupervisedRow, ...],
) -> TemporalSplit:
    cutoffs: dict[str, str] = {}
    for name, rows in (("train", train), ("validation", validation), ("test", test)):
        if rows:
            cutoffs[f"{name}_start"] = min(row.input_started_at for row in rows).isoformat()
            cutoffs[f"{name}_end"] = max(row.target_started_at for row in rows).isoformat()
    return TemporalSplit(
        train,
        validation,
        test,
        cutoffs,
        {
            "train": len({row.group_id for row in train}),
            "validation": len({row.group_id for row in validation}),
            "test": len({row.group_id for row in test}),
        },
        {
            "train": tuple(row.row_id for row in train),
            "validation": tuple(row.row_id for row in validation),
            "test": tuple(row.row_id for row in test),
        },
    )
