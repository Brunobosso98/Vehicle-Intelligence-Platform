# ADR 0024: Bounded tool feedback and optional recipe needs

- Date: 2026-10-14
- Status: Accepted for implementation; real confirmation pending.

## Context

Affected real observations included two parent runs terminated by oversized tool responses and seven thermal-tool rejections. Parent orchestration already returned a safe failure category for MCP tool errors, while specialist orchestration ended the role immediately. A separate real investigation requested useful alternatives to an unavailable signal, but an optional channel with unknown source support prevented selection of any existing recipe.

## Decision

Return only the fixed failure category for `mcp_tool_error` and `tool_result_budget_exhausted` to the requesting model. Keep the original failed tool audit, charge the attempted call, publish no evidence or cache entry, and retain every existing tool, model-turn, byte, timeout and spend limit. The model may choose a smaller compatible read or declare insufficiency within the existing loop. Transport failures, ownership violations, policy failures and exhausted budgets continue to fail safely. No automatic retry or deterministic replacement answer is introduced. The supervisor configuration hash includes tool-error-feedback version 1.0.

An optional acquisition need with unsupported or unknown support from a trusted source does not constrain selection of the recipe for supported needs. Preserve that need, its actual availability, rationale and explicit dropped-signal entry. Required needs still constrain recipe coverage. Before a trusted source is available, retain unknown channels in recipe selection and report an unverified proposal as not feasible. Recipes remain from the unchanged versioned Phase 4 catalog; recipe configuration hashes, signal definitions and the sampling algorithm do not change. Source preflight and explicit user approval remain mandatory.

## Evidence and limits

The optional-channel regression failed before the correction; the negative required-channel case passed. The corrected planner applied independently to the immutable round-thirteen G05 plan selects `performance-pull` with `FEASIBLE_WITH_DEGRADATION`, retaining ignition timing as unavailable and lambda as unknown and listing both dropped channels. This independent review does not change historical scores or establish real-model acceptance.

Production-dispatch tests cover safe tool failure feedback, rejection of oversized payloads before evidence/cache publication, charged attempts, transport failure and existing policy/ownership/budget rejection. Related tests passed 183 cases. Full real confirmation and exact-final-head canonical validation remain required. Graph updates remain deferred under the user's explicit instruction.

Integrated `make check-api` passed 829 tests, typing/lint and coverage (96.06% line, 91.43% branch). Real acceptance remains unverified.
