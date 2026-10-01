"""Validate local skills, scoped context, declarative YAML and Markdown links."""

import os
import re
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
ignored = {
    "node_modules",
    ".venv",
    ".next",
    ".cache",
    ".git",
    ".validation",
    "coverage",
    "test-results",
    "playwright-report",
}
files: list[Path] = []
for directory, directories, filenames in os.walk(root):
    directories[:] = [name for name in directories if name not in ignored]
    files.extend(Path(directory) / filename for filename in filenames)

for path in files:
    if path.suffix in {".yaml", ".yml"}:
        yaml.safe_load(path.read_text())
    if path.suffix == ".md":
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            target = target.split("#", 1)[0].strip("<>")
            if not target or re.match(r"[a-zA-Z]+:", target):
                continue
            if not (path.parent / target).exists():
                raise ValueError(
                    f"Broken local link in {path.relative_to(root)}: {target}"
                )
for path in (root / ".agents/skills").glob("*/SKILL.md"):
    metadata = yaml.safe_load(path.read_text().split("---", 2)[1])
    if metadata.get("name") != path.parent.name or not metadata.get("description"):
        raise ValueError(f"Invalid skill metadata: {path}")
for directory in [".", "apps/api", "apps/web", "packages/contracts", "infra"]:
    if not (root / directory / "AGENTS.md").is_file():
        raise ValueError(f"Missing scoped context: {directory}")
print("YAML, local documentation links, five AGENTS files and four skills validated.")
