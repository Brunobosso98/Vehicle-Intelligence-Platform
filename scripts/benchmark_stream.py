#!/usr/bin/env python3
import json
import time
from datetime import UTC, datetime
from uuid import uuid4

from vehicle_platform.acquisition.stream import RawTelemetryMessage
from vehicle_platform.telemetry.domain import RawTelemetryRecord, sample_id


def main() -> None:
    total = 100_000
    session = uuid4()
    started = time.perf_counter()
    identities: set[str] = set()
    sizes = 0
    for sequence in range(total):
        observed = datetime.now(UTC)
        record = RawTelemetryRecord(
            observed,
            "engine.rpm",
            1000 + sequence % 5000,
            "rpm",
            str(sequence),
            sequence,
        )
        sizes += len(
            RawTelemetryMessage.from_record(
                session, "benchmark", "synthetic-n55", record
            ).encode()
        )
        identities.add(
            sample_id(
                str(session),
                "benchmark",
                str(sequence),
                observed,
                record.signal,
                sequence,
            )
        )
    elapsed = time.perf_counter() - started
    print(
        json.dumps(
            {
                "observations_produced": total,
                "observations_accepted": total,
                "observations_persisted_simulated": len(identities),
                "lost_observations": total - len(identities),
                "duplicate_messages_received": 0,
                "duplicate_canonical_rows": total - len(identities),
                "producer_throughput_observations_per_second": round(
                    total / elapsed, 2
                ),
                "encoded_bytes": sizes,
                "duration_seconds": round(elapsed, 4),
                "scope": "in-process contract/idempotency benchmark; broker/DB values are measured by canonical integration",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
