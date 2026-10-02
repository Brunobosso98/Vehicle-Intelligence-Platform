"""Enforce image vulnerability policy against machine-readable Trivy reports."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--exceptions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_findings(report: Path) -> list[dict[str, Any]]:
    payload = json.loads(report.read_text())
    findings: list[dict[str, Any]] = []
    for result in payload.get("Results") or []:
        for finding in result.get("Vulnerabilities") or []:
            if finding.get("Severity") in {"HIGH", "CRITICAL"}:
                findings.append(finding)
    return findings


def load_exceptions(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text()) or {}
    if payload.get("version") != 1:
        raise ValueError("container risk acceptance file must use version 1")
    exceptions = payload.get("exceptions") or []
    today = dt.datetime.now(dt.UTC).date()
    for item in exceptions:
        required = {"id", "images", "vulnerability_id", "owner", "expires", "rationale"}
        missing = required - set(item)
        if missing:
            raise ValueError(
                f"exception {item.get('id', '<unknown>')} missing: {sorted(missing)}"
            )
        expires = dt.date.fromisoformat(str(item["expires"]))
        if expires < today:
            raise ValueError(f"exception {item['id']} expired on {expires.isoformat()}")
    return exceptions


def accepted(
    image: str, finding: dict[str, Any], exceptions: list[dict[str, Any]]
) -> str | None:
    vulnerability_id = finding.get("VulnerabilityID")
    package = finding.get("PkgName")
    for item in exceptions:
        if image not in item["images"]:
            continue
        if vulnerability_id != item["vulnerability_id"]:
            continue
        allowed_packages = item.get("packages")
        if allowed_packages and package not in allowed_packages:
            continue
        return str(item["id"])
    return None


def main() -> int:
    args = parse_args()
    findings = load_findings(args.report)
    exceptions = load_exceptions(args.exceptions)

    blocked: list[dict[str, str]] = []
    accepted_high: list[dict[str, str]] = []

    for finding in findings:
        record = {
            "id": str(finding.get("VulnerabilityID")),
            "severity": str(finding.get("Severity")),
            "package": str(finding.get("PkgName")),
            "installed_version": str(finding.get("InstalledVersion") or ""),
            "fixed_version": str(finding.get("FixedVersion") or ""),
        }
        if record["severity"] == "CRITICAL":
            blocked.append(record)
            continue
        exception_id = accepted(args.image, finding, exceptions)
        if exception_id is None:
            blocked.append(record)
        else:
            record["exception_id"] = exception_id
            accepted_high.append(record)

    summary = {
        "image": args.image,
        "critical_count": sum(
            1 for item in findings if item.get("Severity") == "CRITICAL"
        ),
        "high_count": sum(1 for item in findings if item.get("Severity") == "HIGH"),
        "accepted_high_count": len(accepted_high),
        "blocked_count": len(blocked),
        "accepted_high": accepted_high,
        "blocked": blocked,
        "status": "PASS" if not blocked else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"{args.image}: {summary['status']} "
        f"(critical={summary['critical_count']}, high={summary['high_count']}, "
        f"accepted_high={summary['accepted_high_count']}, blocked={summary['blocked_count']})"
    )
    return 0 if not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
