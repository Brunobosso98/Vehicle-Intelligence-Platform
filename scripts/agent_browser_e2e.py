"""Dedicated browser gate: controlled real API, authenticated HTTP MCP and TimescaleDB."""

import asyncio
import json
import os
from pathlib import Path

from agent_fixtures import seed_agent
from agent_runtime import runtime

FIXTURE = Path(".validation/agent/browser-fixtures.json").resolve()


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_agent(url)
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(fixture))
    async with runtime(url, web=True) as stack:
        child = await asyncio.create_subprocess_exec(
            "pnpm",
            "--filter",
            "@vehicle-platform/web",
            "exec",
            "playwright",
            "test",
            "agent.spec.ts",
            env=os.environ
            | {"WEB_BASE_URL": stack["web"], "AGENT_E2E_FIXTURE_FILE": str(FIXTURE)},
        )
        assert await child.wait() == 0, "Agent browser E2E failed"
    print(
        json.dumps({"agent_browser_e2e": "PASS", "transport": "authenticated HTTP MCP"})
    )


if __name__ == "__main__":
    asyncio.run(main())
