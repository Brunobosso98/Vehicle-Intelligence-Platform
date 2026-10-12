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

from vehicle_platform.agents.config import AgentSettings, redact_data
from vehicle_platform.agents.investigation.proposal import InvestigationInput, InvestigationProposal
from vehicle_platform.agents.prompts import INVESTIGATION_POLICY, SYSTEM_POLICY
from vehicle_platform.agents.provider import (
    AgentError,
    ModelInput,
    ModelTurn,
    RoutingInput,
    ToolRequest,
)
from vehicle_platform.agents.receipts import ResponseObserver
from vehicle_platform.agents.schemas import Draft, RoutingProposal, Usage
from vehicle_platform.agents.specialists.policy import SUPERVISOR_POLICY, specialist_policy


class OpenAIProvider:
    def __init__(self, settings: AgentSettings, observer: ResponseObserver | None = None) -> None:
        if not settings.api_key or not settings.model:
            raise AgentError("provider_configuration")
        self.settings = settings
        self.observer = observer
        self.client = AsyncOpenAI(
            api_key=settings.api_key.get_secret_value(),
            max_retries=0,
            timeout=settings.model_timeout,
        )

    async def _create(self, role: str, **kwargs: Any) -> tuple[Any, str | None]:
        kwargs["service_tier"] = self.settings.service_tier
        if self.settings.reasoning_effort is not None:
            kwargs["reasoning"] = {"effort": self.settings.reasoning_effort}
        ticket = (
            self.observer.begin(role, len(json.dumps(kwargs).encode()), kwargs["max_output_tokens"])
            if self.observer
            else None
        )
        try:
            return await self.client.responses.create(**kwargs), ticket
        except BaseException as error:
            category = (
                "provider_authentication"
                if isinstance(error, AuthenticationError)
                else "provider_rate_limit"
                if isinstance(error, RateLimitError)
                else "provider_timeout"
                if isinstance(error, (APITimeoutError, TimeoutError))
                else "provider_unavailable"
                if isinstance(error, (APIConnectionError, APIStatusError))
                else "invalid_model_response"
            )
            if isinstance(error, APIStatusError) and error.status_code in {400, 402, 403, 404, 422}:
                body = error.body if isinstance(error.body, dict) else {}
                details = body.get("error", body)
                param = details.get("param") if isinstance(details, dict) else None
                category = (
                    "provider_service_tier_unavailable"
                    if param == "service_tier"
                    else "provider_authentication"
                    if error.status_code == 403
                    else "provider_configuration"
                )
            if self.observer and ticket:
                self.observer.failed(ticket, category)
            if not isinstance(error, Exception):
                raise
            raise AgentError(category) from None

    def _record(self, response: Any, ticket: str | None) -> None:
        if not self.observer or not ticket:
            return
        usage = getattr(response, "usage", None)
        self.observer.complete(
            ticket,
            redact_data(
                {
                    "requested_tools": [
                        item.name
                        for item in getattr(response, "output", [])
                        if item.type == "function_call"
                    ],
                    "model": getattr(response, "model", None),
                    "service_tier": getattr(response, "service_tier", None),
                    "input_tokens": getattr(usage, "input_tokens", None),
                    "output_tokens": getattr(usage, "output_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                    "cached_input_tokens": getattr(
                        getattr(usage, "input_tokens_details", None), "cached_tokens", None
                    ),
                    "reasoning_tokens": getattr(
                        getattr(usage, "output_tokens_details", None), "reasoning_tokens", None
                    ),
                },
                self.settings,
            ),
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
            "specialist_scope": (
                request.specialist.model_dump(mode="json") if request.specialist else None
            ),
            "supervisor": request.supervisor,
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
        receipt: str | None = None
        try:
            async with asyncio.timeout(self.settings.model_timeout):
                stream, receipt = await self._create(
                    request.specialist.specialist.value
                    if request.specialist
                    else "synthesis"
                    if request.supervisor
                    else "agent",
                    model=self.settings.model,
                    instructions=(
                        SYSTEM_POLICY + specialist_policy(request.specialist.specialist)
                        if request.specialist
                        else SYSTEM_POLICY + SUPERVISOR_POLICY
                        if request.supervisor
                        else SYSTEM_POLICY
                    ),
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
                    max_output_tokens=self.settings.max_output_tokens,
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
                            self._record(response, receipt)
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
        finally:
            if self.observer and receipt:
                self.observer.failed(receipt)

    async def route(self, request: RoutingInput) -> RoutingProposal:
        encoded = json.dumps(request.__dict__)
        if len(encoded.encode()) > self.settings.max_input_bytes:
            raise AgentError("model_input_budget_exhausted")
        # Usage is provider metadata, never a field for the model to invent.
        schema = RoutingProposal.model_json_schema()
        schema["properties"].pop("usage")
        schema["$defs"].pop("Usage")
        schema["required"] = ["intent", "specialists"]
        receipt: str | None = None
        try:
            async with asyncio.timeout(self.settings.model_timeout):
                response, receipt = await self._create(
                    "supervisor",
                    model=self.settings.model,
                    instructions=SUPERVISOR_POLICY,
                    input=cast(
                        ResponseInputParam,
                        [{"role": "user", "content": "Untrusted routing data:\n" + encoded}],
                    ),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "supervisor_routing",
                            "schema": schema,
                            "strict": True,
                        }
                    },
                    max_output_tokens=512,
                    store=False,
                )
                self._record(response, receipt)
            if len(response.output_text.encode()) > self.settings.max_output_bytes:
                raise AgentError("model_output_budget_exhausted")
            proposal = RoutingProposal.model_validate_json(response.output_text)
            usage = response.usage
            proposal.usage = Usage(
                input_tokens=usage.input_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
                total_tokens=usage.total_tokens if usage else None,
                cached_input_tokens=usage.input_tokens_details.cached_tokens if usage else None,
            )
            return proposal
        except AuthenticationError:
            raise AgentError("provider_authentication") from None
        except RateLimitError:
            raise AgentError("provider_rate_limit") from None
        except (APITimeoutError, TimeoutError):
            raise AgentError("provider_timeout") from None
        except (APIConnectionError, APIStatusError):
            raise AgentError("provider_unavailable") from None
        except (ValidationError, ValueError, TypeError):
            raise AgentError("invalid_supervisor_routing") from None
        finally:
            if self.observer and receipt:
                self.observer.failed(receipt)

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        payload = {
            "question": request.question,
            "vehicle_context": request.context,
            "current_run_evidence": request.evidence,
            "missing_evidence": request.missing_evidence,
            "supervisor": request.supervisor,
        }
        encoded = json.dumps(payload)
        if len(encoded.encode()) > self.settings.max_input_bytes:
            raise AgentError("model_input_budget_exhausted")
        receipt: str | None = None
        try:
            async with asyncio.timeout(self.settings.model_timeout):
                response, receipt = await self._create(
                    "investigation",
                    model=self.settings.model,
                    instructions=INVESTIGATION_POLICY,
                    input=cast(
                        ResponseInputParam,
                        [{"role": "user", "content": "Untrusted current-run data:\n" + encoded}],
                    ),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "investigation_proposal",
                            "schema": InvestigationProposal.model_json_schema(),
                            "strict": False,
                        }
                    },
                    max_output_tokens=2048,
                    store=False,
                )
                self._record(response, receipt)
            if len(response.output_text.encode()) > self.settings.max_output_bytes:
                raise AgentError("model_output_budget_exhausted")
            return InvestigationProposal.model_validate_json(response.output_text)
        except AuthenticationError:
            raise AgentError("provider_authentication") from None
        except RateLimitError:
            raise AgentError("provider_rate_limit") from None
        except (APITimeoutError, TimeoutError):
            raise AgentError("provider_timeout") from None
        except (APIConnectionError, APIStatusError):
            raise AgentError("provider_unavailable") from None
        except (ValidationError, ValueError, TypeError):
            raise AgentError("invalid_investigation_proposal") from None
        finally:
            if self.observer and receipt:
                self.observer.failed(receipt)

    async def close(self) -> None:
        await self.client.close()
