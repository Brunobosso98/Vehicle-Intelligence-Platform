"""Render measured Phase 9G benchmark and observability receipts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, cast


def _receipt(path: Path) -> dict[str, Any]:
    receipt = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    expected = (
        os.environ.get("GIT_COMMIT_SHA")
        or subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    if (
        receipt.get("final_sha") != expected
        or receipt.get("engineering_status") != "PASS"
    ):
        raise SystemExit("Phase 9G report does not match the current passing commit")
    independent = path.parent / "independent-check.json"
    if not independent.is_file():
        raise SystemExit("independent Phase 9G acceptance receipt is missing")
    checked = json.loads(independent.read_text(encoding="utf-8"))
    if (
        checked.get("independent_status") != "PASS"
        or checked.get("final_sha") != expected
    ):
        raise SystemExit(
            "independent Phase 9G checker did not pass on the current commit"
        )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("benchmark", "observability"))
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        default=Path(".validation/phase9g/acceptance.json"),
    )
    args = parser.parse_args()
    receipt = _receipt(args.report)
    key = "benchmark" if args.mode == "benchmark" else "observability"
    print(
        json.dumps(
            {"final_sha": receipt["final_sha"], key: receipt[key]},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
