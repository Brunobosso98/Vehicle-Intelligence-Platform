import asyncio
import json
from typing import Any, cast

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from openai.types.responses import ResponseInputParam, ToolParam
from pydantic import ValidationError

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.prompts import SYSTEM_POLICY
from vehicle_platform.agents.provider import AgentError, ModelInput, ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Draft, Usage


class OpenAIProvider:
    def __init__(self, settings: AgentSettings) -> None:
        if not settings.api_key or not settings.model:
            raise AgentError("provider_configuration")
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.api_key.get_secret_value(),
            max_retries=0,
            timeout=settings.model_timeout,
        )

    async def turn(self, request: ModelInput) -> ModelTurn:
        tools = [
            {
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
                "strict": False,
            }
            for tool in request.tools
        ]
        public_data = {
            "vehicle_context": request.context,
            "evidence": request.evidence,
            "correction": request.correction,
        }
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": request.question},
            {
                "role": "developer",
                "content": "Current-run untrusted DATA:\n" + json.dumps(public_data),
            },
            *request.messages,
        ]
        if len(json.dumps(messages).encode()) > self.settings.max_input_bytes:
            raise AgentError("model_input_budget_exhausted")
        try:
            async with asyncio.timeout(self.settings.model_timeout):
                stream = await self.client.responses.create(
                    model=self.settings.model,
                    instructions=SYSTEM_POLICY,
                    input=cast(ResponseInputParam, messages),
                    tools=cast(list[ToolParam], tools),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "grounded_draft",
                            "schema": Draft.model_json_schema(),
                            "strict": False,
                        }
                    },
                    max_output_tokens=4096,
                    store=False,
                    stream=True,
                    parallel_tool_calls=False,
                )
                response = None
                received = 0
                async with stream:
                    async for event in stream:
                        if event.type in {
                            "response.output_text.delta",
                            "response.function_call_arguments.delta",
                        }:
                            received += len(event.delta.encode())
                            if received > self.settings.max_output_bytes:
                                raise AgentError("model_output_budget_exhausted")
                        elif event.type == "response.completed":
                            response = event.response
                        elif event.type in {"response.failed", "response.incomplete", "error"}:
                            raise AgentError("invalid_model_response")
                if response is None:
                    raise AgentError("invalid_model_response")
            completed_bytes = len(response.output_text.encode()) + sum(
                len(item.arguments.encode())
                for item in response.output
                if item.type == "function_call"
            )
            if completed_bytes > self.settings.max_output_bytes:
                raise AgentError("model_output_budget_exhausted")
            calls = []
            for item in response.output:
                if item.type == "function_call":
                    arguments = json.loads(item.arguments)
                    if not isinstance(arguments, dict):
                        raise AgentError("invalid_model_response")
                    calls.append(
                        ToolRequest(call_id=item.call_id, name=item.name, arguments=arguments)
                    )
            usage = response.usage
            return ModelTurn(
                tool_calls=calls,
                draft=Draft.model_validate_json(response.output_text) if not calls else None,
                usage=Usage(
                    input_tokens=usage.input_tokens if usage else None,
                    output_tokens=usage.output_tokens if usage else None,
                    total_tokens=usage.total_tokens if usage else None,
                    cached_input_tokens=usage.input_tokens_details.cached_tokens if usage else None,
                ),
            )
        except AuthenticationError:
            raise AgentError("provider_authentication") from None
        except RateLimitError:
            raise AgentError("provider_rate_limit") from None
        except (APITimeoutError, TimeoutError):
            raise AgentError("provider_timeout") from None
        except (APIConnectionError, APIStatusError):
            raise AgentError("provider_unavailable") from None
        except (ValidationError, ValueError, TypeError):
            raise AgentError("invalid_model_response") from None

    async def close(self) -> None:
        await self.client.close()
