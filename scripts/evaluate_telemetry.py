"""Phase 1 parser/normalization/identity acceptance independent of pytest."""

import asyncio
import json
from datetime import UTC, datetime

from vehicle_platform.telemetry.domain import (
    SIGNAL_BY_ALIAS,
    normalize_value,
    sample_id,
)
from vehicle_platform.telemetry.sources import CSVTelemetrySource


async def main() -> None:
    content = (
        b"timestamp,signal,value,unit,record_id,sequence\n"
        b"2026-01-01T01:00:01+01:00,speed,36,km/h,speed,2\n"
        b"2026-01-01T00:00:00Z,boost,-0.3,bar,boost,1\n"
        b"2026-01-01T00:00:00Z,iat,20,C,temperature,3\n"
    )
    records = [r async for r in CSVTelemetrySource(content).read()]
    values = [
        normalize_value(r.value, r.unit, SIGNAL_BY_ALIAS[r.signal])[0] for r in records
    ]
    identities = [
        sample_id(
            "session", "csv", r.source_record_id, r.observed_at, r.signal, r.sequence
        )
        for r in records
    ]
    checks = {
        "canonical_units": values == [10, -30000, 293.15],
        "UTC": records[0].observed_at == datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
        "distinct_identity": len(set(identities)) == 3,
        "replay_identity": identities
        == [
            sample_id(
                "session",
                "csv",
                r.source_record_id,
                r.observed_at,
                r.signal,
                r.sequence,
            )
            for r in records
        ],
    }
    for name, bad in (
        ("formula", content.replace(b"36,km/h", b"=1+1,km/h")),
        ("missing_column", content.replace(b",sequence", b"")),
        (
            "naive_timestamp",
            content.replace(b"2026-01-01T00:00:00Z", b"2026-01-01T00:00:00"),
        ),
    ):
        try:
            [r async for r in CSVTelemetrySource(bad).read()]
        except ValueError:
            checks[name] = True
        else:
            checks[name] = False
    print(
        json.dumps(
            {
                "phase": 1,
                "checks": checks,
                "persistence": "make test-integration required",
            },
            indent=2,
        )
    )
    if not all(checks.values()):
        raise SystemExit("Phase 1 acceptance failed")


if __name__ == "__main__":
    asyncio.run(main())
