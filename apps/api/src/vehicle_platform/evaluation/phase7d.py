"""Versioned suite, conservative pricing, and crash-safe paid-call accounting."""

import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import Field, model_validator

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import StrictModel

ROLES = frozenset({"data_quality", "performance", "thermal", "fuel_air_boost"})
CRITICAL = frozenset(
    "C08 C10 D08 D09 D10 E05 F01 F03 F04 F08 G01 G02 G04 G06 G08 G09 H01 H03 H05 H07".split()
)


class Case(StrictModel):
    case_id: str = Field(pattern=r"^[A-H](0[1-9]|10)$")
    category: str = Field(pattern=r"^[A-H]$")
    question: str = Field(min_length=1, max_length=2000)
    fixture: Literal["normal", "thermal", "mixed", "poor", "comparison", "sparse_comparison"]
    required_specialists: list[str]
    allowed_optional_specialists: list[str]
    forbidden_specialists: list[str]
    required_tools: list[str]
    forbidden_tools: list[str]
    expect_insufficient: bool
    expect_phase7b: bool | None
    required_signal_roles: list[str]
    require_recipe: bool
    critical: bool
    repeat_count: Literal[0, 2]
    grading_rules: dict[str, Any]

    @model_validator(mode="after")
    def consistent(self) -> "Case":
        groups = [
            self.required_specialists,
            self.allowed_optional_specialists,
            self.forbidden_specialists,
        ]
        flat = [role for group in groups for role in group]
        if len(flat) != len(set(flat)) or set(flat) != ROLES:
            raise ValueError("specialist constraints must partition the registry")
        if self.category != self.case_id[0] or self.critical != (self.case_id in CRITICAL):
            raise ValueError("case identity or critical subset mismatch")
        if self.repeat_count != (2 if self.critical else 0):
            raise ValueError("critical cases require exactly two additional runs")
        return self


class Suite(StrictModel):
    version: Literal["phase7d-v1"]
    fixture_version: Literal["phase7d-canonical-v1"]
    cases: list[Case]

    @model_validator(mode="after")
    def exact_suite(self) -> "Suite":
        expected = {f"{group}{index:02}" for group in "ABCDEFGH" for index in range(1, 11)}
        if len(self.cases) != 80 or {case.case_id for case in self.cases} != expected:
            raise ValueError("suite must contain the exact 80 unique cases")
        if len({case.question for case in self.cases}) != 80:
            raise ValueError("questions must be unique")
        if Counter(case.category for case in self.cases) != Counter(dict.fromkeys("ABCDEFGH", 10)):
            raise ValueError("each category requires ten questions")
        if {case.case_id for case in self.cases if case.critical} != CRITICAL:
            raise ValueError("suite requires the exact 20 critical cases")
        return self

    def schedule(self) -> list[tuple[Case, int]]:
        return [(case, 0) for case in self.cases] + [
            (case, repeat) for repeat in (1, 2) for case in self.cases if case.critical
        ]


def load_suite(path: Path) -> tuple[Suite, str]:
    raw = path.read_bytes()
    return Suite.model_validate_json(raw), hashlib.sha256(raw).hexdigest()


class Rates(StrictModel):
    model: Literal["gpt-6-luna"] = "gpt-6-luna"
    service_tier: Literal["flex"] = "flex"
    verified_on: str = "2026-10-12"
    source: str = "https://developers.openai.com/api/docs/models/gpt-6-luna"
    input_per_million: Decimal = Decimal("0.05")
    cached_per_million: Decimal = Decimal("0.005")
    output_per_million: Decimal = Decimal("0.25")

    @model_validator(mode="after")
    def valid_rates(self) -> "Rates":
        for rate in (self.input_per_million, self.cached_per_million, self.output_per_million):
            if not rate.is_finite() or rate < 0:
                raise ValueError("rates must be finite and nonnegative")
        datetime.strptime(self.verified_on, "%Y-%m-%d")
        return self

    def cost(self, input_tokens: int, cached: int, output: int) -> dict[str, str]:
        if min(input_tokens, cached, output) < 0 or cached > input_tokens or input_tokens > 272000:
            raise AgentError("invalid_usage_or_long_context")
        parts = {
            "input": Decimal(input_tokens - cached) * self.input_per_million / 1000000,
            "cached_input": Decimal(cached) * self.cached_per_million / 1000000,
            "output": Decimal(output) * self.output_per_million / 1000000,
        }
        return {key: str(value) for key, value in parts.items()} | {
            "total": str(sum(parts.values(), Decimal(0)))
        }


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as target:
        json.dump(value, target, indent=2, ensure_ascii=False, allow_nan=False)
        target.write("\n")
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class Ledger:
    """Caller holds an exclusive filesystem lock for this ledger's whole lifetime.

    Every call reserves its worst-case cost before network I/O. Unknown usage retains
    the reservation. A completed response replaces it with reported usage, even when
    the public JSON later fails validation. An interrupted case is never auto-replayed.
    """

    def __init__(
        self,
        path: Path,
        identity: dict[str, Any],
        limit: Decimal,
        rates: Rates,
        *,
        confirmation: bool = False,
        operator_extra: bool = False,
    ) -> None:
        if not limit.is_finite() or not Decimal(0) < limit <= Decimal(5):
            raise AgentError("invalid_spend_limit")
        self.path, self.rates, self.limit = path, rates, limit
        self.started: dict[str, float] = {}
        self.case_key = "smoke"
        self.state: dict[str, Any]
        if operator_extra and not confirmation:
            raise AgentError("operator_extra_requires_confirmation")
        if path.exists():
            self.state = json.loads(path.read_text())
            if self.state["rates"] != rates.model_dump(mode="json"):
                raise AgentError("checkpoint_pricing_mismatch")
            if confirmation:
                if self.state["round"] >= 2 and not operator_extra:
                    raise AgentError("full_suite_limit")
                if operator_extra and self.state["round"] < 2:
                    raise AgentError("operator_extra_requires_two_previous_rounds")
                self.state["round"] += 1
                self.state["identities"].append(identity)
                self.state.pop("projection", None)
                if operator_extra:
                    history = self.state.setdefault("operator_extra_confirmations", [])
                    previous = self.state.get("operator_extra_confirmation")
                    if previous and previous not in history:
                        history.append(previous)
                    confirmation_record = {
                        "round": self.state["round"],
                        "requested_at": datetime.now(UTC).isoformat(),
                    }
                    history.append(confirmation_record)
                    self.state["operator_extra_confirmation"] = confirmation_record
            elif self.state["identities"][-1] != identity:
                raise AgentError("checkpoint_identity_mismatch")
        elif confirmation:
            raise AgentError("confirmation_requires_initial_suite")
        else:
            self.state = {
                "schema_version": "1.0",
                "round": 1,
                "identities": [identity],
                "rates": rates.model_dump(mode="json"),
                "calls": {},
                "results": {},
                "smoke": None,
                "active": None,
                "created_at": datetime.now(UTC).isoformat(),
            }
        if self.state["active"]:
            key = self.state["active"]
            self.state["results"].setdefault(
                key,
                {
                    "status": "INTERRUPTED",
                    "case_key": key,
                    "run_id": self.state.get("active_run_id"),
                },
            )
            self.state["active"] = None
        self.save()

    def save(self) -> None:
        self.state["estimated_spend_usd"] = str(self.spend())
        self.state["configured_limit_usd"] = str(self.limit)
        atomic_json(self.path, self.state)

    def spend(self) -> Decimal:
        return sum(
            (Decimal(call["cost"]["total"]) for call in self.state["calls"].values()), Decimal(0)
        )

    def key(self, case: Case, repeat: int) -> str:
        return f"{self.state['round']}:{case.case_id}:{repeat}"

    def start_case(self, key: str) -> bool:
        if key in self.state["results"]:
            return False
        self.case_key = key
        self.state["active"] = key
        self.state.pop("active_run_id", None)
        self.save()
        return True

    def finish_case(self, key: str, result: dict[str, Any]) -> None:
        self.state["results"][key] = result
        self.state["active"] = None
        self.state.pop("active_run_id", None)
        self.save()

    def begin(self, role: str, input_bytes: int, max_output_tokens: int) -> str:
        calls = [call for call in self.state["calls"].values() if call["case_key"] == self.case_key]
        # 16 production steps + one infrastructure retry + one Phase 7B proposal.
        if len(calls) >= (3 if self.case_key == "smoke" else 18):
            raise AgentError("BUDGET_VIOLATION")
        if sum(call["status"] == "failed" for call in calls) > 1:
            raise AgentError("provider_retry_budget_exhausted")
        # UTF-8 bytes conservatively bound token count, with protocol overhead.
        upper_input = input_bytes + 2048
        cost = self.rates.cost(upper_input, 0, max_output_tokens)
        if self.spend() + Decimal(cost["total"]) > self.limit:
            raise AgentError("SKIPPED_BUDGET_LIMIT")
        ticket = str(uuid4())
        self.state["calls"][ticket] = {
            "case_key": self.case_key,
            "role": role,
            "status": "reserved",
            "input_bound": upper_input,
            "output_bound": max_output_tokens,
            "cost": cost,
            "usage": None,
            "started_at": datetime.now(UTC).isoformat(),
        }
        self.started[ticket] = perf_counter()
        self.save()
        return ticket

    def complete(self, ticket: str, metadata: dict[str, Any]) -> None:
        call = self.state["calls"][ticket]
        if call["status"] != "reserved":
            raise AgentError("duplicate_provider_receipt")
        usage = {
            name: metadata.get(name)
            for name in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "total_tokens",
                "reasoning_tokens",
            )
        }
        for name in ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens"):
            if not isinstance(usage[name], int) or isinstance(usage[name], bool):
                raise AgentError("provider_usage_unavailable")
        counts = cast(dict[str, int], usage)
        if (
            counts["input_tokens"] > call["input_bound"]
            or counts["output_tokens"] > call["output_bound"]
            or counts["total_tokens"] != counts["input_tokens"] + counts["output_tokens"]
        ):
            raise AgentError("BUDGET_VIOLATION")
        cost = self.rates.cost(
            counts["input_tokens"], counts["cached_input_tokens"], counts["output_tokens"]
        )
        call.update(
            status="completed",
            requested_tools=metadata.get("requested_tools", []),
            usage=usage,
            cost=cost,
            model=metadata.get("model"),
            service_tier=metadata.get("service_tier"),
            duration_seconds=perf_counter() - self.started.pop(ticket),
        )
        self.save()
        if metadata.get("model") != self.rates.model or metadata.get("service_tier") != "flex":
            raise AgentError("provider_configuration_mismatch")

    def failed(self, ticket: str, category: str | None = None) -> None:
        call = self.state["calls"][ticket]
        if call["status"] != "reserved":
            return
        call.update(
            status="failed",
            error_category=category or "unknown_usage",
            duration_seconds=perf_counter() - self.started.pop(ticket),
        )
        # Timeout/transport errors can be billable. Keep the upper bound and stop
        # after at most one retry; do not assume that no response means no spend.
        self.save()
