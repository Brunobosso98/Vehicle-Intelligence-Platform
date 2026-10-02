from dataclasses import dataclass
from statistics import fmean

from vehicle_platform.events.domain import EventCandidate
from vehicle_platform.events.synthetic import ExpectedEvent


@dataclass(frozen=True)
class EventClassMetrics:
    event_type: str
    expected: int
    detected: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    mean_start_error_seconds: float | None
    mean_end_error_seconds: float | None


@dataclass(frozen=True)
class EventEvaluation:
    by_type: dict[str, EventClassMetrics]
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    mean_start_error_seconds: float | None
    mean_end_error_seconds: float | None


def _overlaps(expected: ExpectedEvent, detected: EventCandidate, tolerance_seconds: float) -> bool:
    if expected.event_type != detected.event_type:
        return False
    if expected.pull_index is not None and expected.pull_index != detected.pull_index:
        return False
    return (
        detected.started_at.timestamp() <= expected.ended_at.timestamp() + tolerance_seconds
        and detected.ended_at.timestamp() >= expected.started_at.timestamp() - tolerance_seconds
    )


def evaluate_events(
    expected: tuple[ExpectedEvent, ...],
    detected: list[EventCandidate],
    tolerance_seconds: float = 0.25,
) -> EventEvaluation:
    """One-to-one deterministic matching by type, pull and temporal overlap."""
    remaining = list(enumerate(detected))
    matched: list[tuple[ExpectedEvent, EventCandidate]] = []
    for truth in sorted(expected, key=lambda item: (item.started_at, item.event_type)):
        candidates = [
            (index, event)
            for index, event in remaining
            if _overlaps(truth, event, tolerance_seconds)
        ]
        if not candidates:
            continue
        chosen = min(
            candidates,
            key=lambda pair: (
                abs((pair[1].started_at - truth.started_at).total_seconds())
                + abs((pair[1].ended_at - truth.ended_at).total_seconds()),
                pair[0],
            ),
        )
        matched.append((truth, chosen[1]))
        remaining.remove(chosen)

    event_types = sorted(
        {item.event_type for item in expected} | {item.event_type for item in detected}
    )
    by_type: dict[str, EventClassMetrics] = {}
    all_start_errors: list[float] = []
    all_end_errors: list[float] = []
    for event_type in event_types:
        expected_count = sum(item.event_type == event_type for item in expected)
        detected_count = sum(item.event_type == event_type for item in detected)
        pairs = [(truth, event) for truth, event in matched if truth.event_type == event_type]
        tp = len(pairs)
        fp, fn = detected_count - tp, expected_count - tp
        precision = tp / detected_count if detected_count else (1.0 if not expected_count else 0.0)
        recall = tp / expected_count if expected_count else (1.0 if not detected_count else 0.0)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        start_errors = [
            abs((event.started_at - truth.started_at).total_seconds()) for truth, event in pairs
        ]
        end_errors = [
            abs((event.ended_at - truth.ended_at).total_seconds()) for truth, event in pairs
        ]
        all_start_errors.extend(start_errors)
        all_end_errors.extend(end_errors)
        by_type[event_type] = EventClassMetrics(
            event_type,
            expected_count,
            detected_count,
            tp,
            fp,
            fn,
            precision,
            recall,
            f1,
            fmean(start_errors) if start_errors else None,
            fmean(end_errors) if end_errors else None,
        )
    tp = len(matched)
    fp, fn = len(detected) - tp, len(expected) - tp
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    values = list(by_type.values())
    return EventEvaluation(
        by_type,
        tp,
        fp,
        fn,
        precision,
        recall,
        2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        fmean(item.precision for item in values) if values else 1.0,
        fmean(item.recall for item in values) if values else 1.0,
        fmean(item.f1 for item in values) if values else 1.0,
        fmean(all_start_errors) if all_start_errors else None,
        fmean(all_end_errors) if all_end_errors else None,
    )
