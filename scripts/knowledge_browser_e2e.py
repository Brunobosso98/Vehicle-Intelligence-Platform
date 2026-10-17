"""Browser proof over disposable knowledge/vehicle fixtures and actual HTTP MCP/API."""

import asyncio
import json
import os
from pathlib import Path

from agent_fixtures import seed_agent
from agent_runtime import runtime
from evaluate_knowledge import seed_knowledge
from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.knowledge.repository import KnowledgeRepository


async def main():
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_agent(url)
    database = Database(Settings(database_url=url, environment="test"))
    try:
        index, _ = await seed_knowledge(KnowledgeRepository(database))
    finally:
        await database.close()
    fixture["knowledge_index"] = index.id
    target = Path(".validation/knowledge/browser-fixtures.json").resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(fixture))
    async with runtime(url, web=True) as stack:
        child = await asyncio.create_subprocess_exec(
            "pnpm",
            "--filter",
            "@vehicle-platform/web",
            "exec",
            "playwright",
            "test",
            "knowledge.spec.ts",
            env=os.environ
            | {"WEB_BASE_URL": stack["web"], "KNOWLEDGE_E2E_FIXTURE_FILE": str(target)},
        )
        assert await child.wait() == 0, "Knowledge browser E2E failed"
    print(
        json.dumps(
            {
                "knowledge_browser_e2e": "PASS",
                "transport": "authenticated HTTP MCP",
                "paid_calls": 0,
                "embedding_provider": "synthetic-free",
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
