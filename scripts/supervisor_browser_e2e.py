"""Phase 7C browser gate over canonical recordings, actual HTTP MCP and disposable DB."""

import asyncio
import json
import os
from pathlib import Path

from agent_runtime import runtime
from supervisor_fixtures import seed_supervisor


async def main():
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_supervisor(url)
    path = Path(".validation/supervisor/browser-fixtures.json").resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture))
    async with runtime(url, web=True) as stack:
        child = await asyncio.create_subprocess_exec(
            "pnpm",
            "--filter",
            "@vehicle-platform/web",
            "exec",
            "playwright",
            "test",
            "supervisor.spec.ts",
            env=os.environ
            | {"WEB_BASE_URL": stack["web"], "SUPERVISOR_E2E_FIXTURE_FILE": str(path)},
        )
        assert await child.wait() == 0, "Supervisor browser E2E failed"
    print(
        json.dumps(
            {"supervisor_browser_e2e": "PASS", "transport": "authenticated HTTP MCP"}
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
