"""Opt-in paid-evaluation traces of public structured I/O, never reasoning or credentials."""

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from vehicle_platform.agents.config import AgentSettings, redact_data
from vehicle_platform.agents.openai_provider import OpenAIProvider
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.receipts import ResponseObserver
from vehicle_platform.evaluation.phase7d import atomic_json


def public_json(value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {"invalid_json": True, "sha256": hashlib.sha256(value.encode()).hexdigest()}


class TracedOpenAIProvider(OpenAIProvider):
    def __init__(
        self, settings: AgentSettings, observer: ResponseObserver, directory: Path
    ) -> None:
        super().__init__(settings, observer)
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.paths: dict[str | None, Path] = {}

    async def _create(self, role: str, **kwargs: Any) -> tuple[Any, str | None]:
        prefix = self.directory / f"{role}-{uuid4()}"
        case_key = getattr(self.observer, "case_key", None)
        if not isinstance(case_key, str):
            case_key = None
        atomic_json(
            prefix.with_suffix(".request.json"),
            redact_data(
                {
                    "role": role,
                    "case_key": case_key,
                    "request": kwargs,
                },
                self.settings,
            ),
        )
        try:
            response, ticket = await super()._create(role, **kwargs)
        except AgentError as error:
            atomic_json(prefix.with_suffix(".failure.json"), {"category": error.category})
            raise
        self.paths[ticket] = prefix
        return response, ticket

    def _record(self, response: Any, ticket: str | None) -> None:
        prefix = self.paths.get(ticket)
        if prefix is not None:
            # Inspect only user-facing structured output and function calls. Never serialize
            # the full SDK response, reasoning items, summaries or transport/auth headers.
            calls = [
                {"name": item.name, "arguments": public_json(item.arguments)}
                for item in getattr(response, "output", [])
                if item.type == "function_call"
            ]
            atomic_json(
                prefix.with_suffix(".response.json"),
                redact_data(
                    {
                        "ticket": ticket,
                        "model": getattr(response, "model", None),
                        "service_tier": getattr(response, "service_tier", None),
                        "public_output": public_json(getattr(response, "output_text", "")),
                        "tool_calls": calls,
                    },
                    self.settings,
                ),
            )
        super()._record(response, ticket)
