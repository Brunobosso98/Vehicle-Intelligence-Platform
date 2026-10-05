from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median

from vehicle_platform.analysis.domain import AlignedFrame, DetectorProfile, Observation


def rolling_median(values: list[float | None], width: int) -> list[float | None]:
    result: list[float | None] = []
    radius = width // 2
    for index in range(len(values)):
        available = [
            item for item in values[max(0, index - radius) : index + radius + 1] if item is not None
        ]
        result.append(float(median(available)) if available else None)
    return result


def align_observations(
    observations: list[Observation], profile: DetectorProfile
) -> list[AlignedFrame]:
    """Align by deterministic last-value carry-forward, expiring at max_gap.

    Duplicate signal/timestamps resolve by sample_id then input value; no linear interpolation is
    performed. Large gaps produce no frames and mark the first frame after the discontinuity.
    """
    if not observations:
        return []
    ordered = sorted(
        observations, key=lambda item: (item.observed_at, item.signal, item.sample_id or "")
    )
    by_signal: dict[str, dict[datetime, Observation]] = defaultdict(dict)
    for item in ordered:
        by_signal[item.signal][item.observed_at.astimezone(UTC)] = item
    times = sorted({item.observed_at.astimezone(UTC) for item in ordered})
    start, end = times[0], times[-1]
    interval = timedelta(milliseconds=profile.interval_ms)
    max_gap = timedelta(seconds=profile.max_gap_seconds)
    streams = {
        key: sorted(values.values(), key=lambda item: item.observed_at)
        for key, values in by_signal.items()
    }
    indexes = {key: 0 for key in streams}
    latest: dict[str, Observation] = {}
    frames: list[AlignedFrame] = []
    cursor = start
    previous_source_time: datetime | None = None
    while cursor <= end:
        for key, stream in streams.items():
            while indexes[key] < len(stream) and stream[indexes[key]].observed_at <= cursor:
                latest[key] = stream[indexes[key]]
                indexes[key] += 1
        values: dict[str, float | None] = {}
        ids: dict[str, str] = {}
        freshest: datetime | None = None
        for key in streams:
            latest_item = latest.get(key)
            if latest_item is not None and cursor - latest_item.observed_at <= max_gap:
                values[key] = latest_item.value
                freshest = (
                    latest_item.observed_at
                    if freshest is None
                    else max(freshest, latest_item.observed_at)
                )
                if latest_item.sample_id:
                    ids[key] = latest_item.sample_id
            else:
                values[key] = None
        if freshest is not None:
            gap = previous_source_time is not None and freshest - previous_source_time > max_gap
            frames.append(AlignedFrame(cursor, values, ids, gap))
            previous_source_time = freshest
        else:
            next_times = [
                stream[indexes[key]].observed_at
                for key, stream in streams.items()
                if indexes[key] < len(stream)
            ]
            if not next_times:
                break
            # Skip only expired, empty grid positions. Keep the original grid
            # origin and gap flag; sparse years must not require years of ticks.
            steps = max(1, (min(next_times) - cursor) // interval)
            cursor += steps * interval
            continue
        cursor += interval
    for signal in ("engine.rpm", "vehicle.speed"):
        smoothed = rolling_median(
            [frame.values.get(signal) for frame in frames], profile.smoothing_window
        )
        frames = [
            AlignedFrame(
                f.observed_at, {**f.values, signal: smoothed[i]}, f.source_sample_ids, f.gap_before
            )
            for i, f in enumerate(frames)
        ]
    return frames
