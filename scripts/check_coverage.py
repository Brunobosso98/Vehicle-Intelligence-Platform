"""Enforce separate line and branch thresholds for the generated local coverage artifact."""

from pathlib import Path
from xml.etree import (
    ElementTree,
)

report = ElementTree.parse(Path("apps/api/coverage.xml")).getroot()
for dimension in ("line", "branch"):
    percent = float(report.attrib[f"{dimension}-rate"]) * 100
    print(f"API {dimension} coverage: {percent:.2f}% (required >=90%)")
    if percent < 90:
        raise SystemExit(f"API {dimension} coverage is below the required threshold")
