"""Write canonical CI validation summaries without converting failures into passes."""

import json
import os
from pathlib import Path

labels = {
    "Cloud validation": "CLOUD",
    "API/Web container builds": "CONTAINERS",
    "Database and migrations": "DATABASE",
    "Canonical stack": "STACK",
    "E2E": "E2E",
    "Container security": "SECURITY",
    "Observability": "OBSERVABILITY",
}
outcome_status = {
    "success": "PASS",
    "failure": "FAIL",
    "cancelled": "NOT RUN",
    "skipped": "NOT RUN",
}
results = {
    label: outcome_status.get(os.environ.get(key, "skipped"), "NOT RUN")
    for label, key in labels.items()
}
full_gate = "PASS" if all(value == "PASS" for value in results.values()) else "FAIL"
payload = {
    "commit": os.environ["GITHUB_SHA"],
    "checks": results,
    "full_gate": full_gate,
}
root = Path("validation-artifacts/summary")
root.mkdir(parents=True, exist_ok=True)
(root / "validation-summary.json").write_text(json.dumps(payload, indent=2) + "\n")
lines = ["PHASE 0 FULL VALIDATION", "", f"Commit: {payload['commit']}", ""]
lines.extend(f"{label:.<32} {status}" for label, status in results.items())
lines.extend(["", f"{'FULL GATE':.<32} {full_gate}"])
summary = "\n".join(lines) + "\n"
(root / "validation-summary.txt").write_text(summary)
with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as handle:
    handle.write("```text\n" + summary + "```\n")
