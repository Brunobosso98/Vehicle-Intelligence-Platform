"""Opt-in billable smoke against controlled fixtures through the real Responses adapter."""

import asyncio
import json
import os

import httpx
from agent_fixtures import seed_agent
from agent_runtime import ask, runtime


async def main() -> None:
    if not os.environ.get("VIP_AGENT_API_KEY") or not os.environ.get("VIP_AGENT_MODEL"):
        raise SystemExit(
            "Real smoke requires VIP_AGENT_API_KEY and VIP_AGENT_MODEL; no request sent"
        )
    url = os.environ["TEST_DATABASE_URL"]
    fixture = await seed_agent(url)
    results = []
    async with (
        runtime(url, real=True) as stack,
        httpx.AsyncClient(base_url=stack["api"], timeout=185) as api,
    ):
        for question in (
            "Qual foi minha última sessão?",
            "Essa peça causou a melhora?",
        ):
            run = await ask(api, fixture["vehicle"], question)
            assert run["status"] == "completed", run["error_category"]
            evidence = {e["id"]: e for e in run["evidence"]}
            for finding in run["result"]["findings"]:
                assert finding["classification"] != "SUPPORTED_CONCLUSION"
                assert all(
                    identifier in evidence for identifier in finding["evidence_ids"]
                )
                for binding in finding["bindings"]:
                    source = evidence[binding["evidence_id"]]
                    assert (
                        source["run_id"] == run["id"]
                        and source["vehicle_id"] == fixture["vehicle"]
                    )
                    assert any(
                        f["path"] == binding["path"]
                        and f["value"] == binding["value"]
                        and f["unit"] == binding["unit"]
                        for f in source["facts"]
                    )
            results.append(
                {
                    "run_id": run["id"],
                    "usage": run["usage"],
                    "duration_seconds": run["duration_seconds"],
                    "tool_count": run["tool_call_count"],
                }
            )
    print(json.dumps({"real_provider_smoke": "PASS", "runs": results}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
