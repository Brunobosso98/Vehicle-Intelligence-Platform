"""Phase 7B browser gate against a disposable real API/MCP/database stack."""

import asyncio
import json
import os
from pathlib import Path

from agent_fixtures import seed_agent
from agent_runtime import runtime

FIXTURE = Path(".validation/investigation/browser-fixtures.json").resolve()


async def main() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_agent(url)
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(fixture))
    async with runtime(url, web=True, worker=True) as stack:
        child = await asyncio.create_subprocess_exec(
            "node",
            "apps/web/node_modules/@playwright/test/cli.js",
            "test",
            "investigation.spec.ts",
            "--config=apps/web/playwright.config.ts",
            env=os.environ
            | {
                "WEB_BASE_URL": stack["web"],
                "INVESTIGATION_E2E_FIXTURE_FILE": str(FIXTURE),
                "INVESTIGATION_E2E_TOKEN": stack["token"],
                "INVESTIGATION_E2E_API": stack["api"],
            },
        )
        assert await child.wait() == 0, "Investigation browser E2E failed"
    print(json.dumps({"investigation_browser_e2e": "PASS"}))


if __name__ == "__main__":
    asyncio.run(main())
