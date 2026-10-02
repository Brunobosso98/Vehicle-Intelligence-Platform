from dataclasses import dataclass
from statistics import fmean, median

from vehicle_platform.analysis.domain import DetectedPull
from vehicle_platform.analysis.synthetic import GroundTruthEvent


@dataclass(frozen=True)
class EvaluationResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    mean_start_error_seconds: float | None
    median_start_error_seconds: float | None
    mean_end_error_seconds: float | None
    median_end_error_seconds: float | None


def evaluate_pulls(
    expected: tuple[GroundTruthEvent, ...],
    detected: list[DetectedPull],
    tolerance_seconds: float = 1.5,
) -> EvaluationResult:
    remaining = list(detected)
    start_errors: list[float] = []
    end_errors: list[float] = []
    matches = 0
    for truth in expected:
        candidates = [
            (abs((item.started_at - truth.started_at).total_seconds()), item) for item in remaining
        ]
        if not candidates:
            continue
        error, match = min(candidates, key=lambda pair: pair[0])
        end_error = abs((match.ended_at - truth.ended_at).total_seconds())
        if error <= tolerance_seconds and end_error <= tolerance_seconds:
            matches += 1
            remaining.remove(match)
            start_errors.append(error)
            end_errors.append(end_error)
    fp, fn = len(remaining), len(expected) - matches
    precision = matches / (matches + fp) if matches + fp else 1.0
    recall = matches / (matches + fn) if matches + fn else 1.0
    return EvaluationResult(
        matches,
        fp,
        fn,
        precision,
        recall,
        2 * precision * recall / (precision + recall) if precision + recall else 0,
        fmean(start_errors) if start_errors else None,
        median(start_errors) if start_errors else None,
        fmean(end_errors) if end_errors else None,
        median(end_errors) if end_errors else None,
    )
