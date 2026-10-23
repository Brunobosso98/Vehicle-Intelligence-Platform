"""Render Phase 9F acceptance measurements without deriving new results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise SystemExit(f"Phase 9F acceptance receipt is not an object: {path}")
    if (
        report.get("schema_version") != "phase9f-agent-integration-v1"
        or report.get("status") != "PASS"
    ):
        raise SystemExit(f"Phase 9F has no passing acceptance receipt: {path}")
    return cast(dict[str, Any], report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("view", choices=("benchmark", "observability"))
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = _report(args.report)
    key = "benchmarks" if args.view == "benchmark" else "observability"
    result = report.get(key)
    if not isinstance(result, dict):
        raise SystemExit(f"Phase 9F receipt is missing {key}: {args.report}")
    if args.view == "observability" and result.get("status") != "PASS":
        raise SystemExit("Phase 9F observability receipt is not passing")
    print(
        json.dumps(
            {"phase9f": args.view, "git_sha": report.get("git_sha"), key: result},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
