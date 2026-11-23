# ADR 0052: Phase 11 holdout and red-team acceptance gates

- Status: Accepted
- Date: 2026-11-22
- Decision owners: Vehicle Intelligence Platform maintainers
- Supplements: [ADR 0051](0051-phase11-independent-agent-evaluation.md)

## Context

ADR 0051 separates the deterministic evaluator from the production agent and preserves the
historical Phase 7D caveat. Phase 11 also needs a clear boundary between visible engineering cases,
independent holdout cases, and attack inputs that exercise real application boundaries. Without
that boundary, a visible suite can be mislabeled as unseen-attack validation, or an attack fixture
can gain capabilities by being placed in a test corpus.

## Decision

- Keep implementation-visible Phase 11 cases as an open engineering corpus. Only a separate,
  frozen corpus selected by independent acceptance may be described as a hidden holdout. Record its
  selector, version and SHA-256 outside implementation-authored scenario metadata. If that artifact
  is absent, report the holdout as absent and Phase 11 as NOT VERIFIED.
- Limit adversarial source mutation to disposable synthetic fixtures. Route malicious text through
  the same production API, LangGraph, MCP and retrieval boundaries under test. Restore every
  mutated row or active index in `finally` and compare a read-only source digest before and after.
- Treat any successful unauthorized action, cross-vehicle access, secret exposure, approval or
  serving bypass, ECU operation, or unsupported safety-clearance claim as a per-case critical veto.
  Do not average it into an aggregate score.
- Keep deterministic runs at zero paid provider calls. Any later paid cohort requires separate
  operator authorization, an exact source SHA, an allowlisted model, and a precommitted cost cap;
  its outcomes remain separate from deterministic and historical results.
- Preserve every attempt in an append-only, content-hashed receipt. A later passing attempt does
  not erase a prior failure, and results from different SHAs are never combined into one pass.

## Alternatives considered

- **Publish a self-authored holdout in the implementation repository:** rejected because it is
  visible to prompt and harness authors and cannot establish independent selection.
- **Treat all visible red-team cases as unseen-attack evidence:** rejected because it confuses
  regression coverage with resistance to unobserved attacks.
- **Allow fixtures to add MCP credentials or production capabilities:** rejected because test data
  must not change authorization policy.
- **Use a weighted score for critical security failures:** rejected because a benign pass rate
  cannot compensate for an unauthorized action or secret leak.

## Consequences and risks

The visible suite remains useful for reproducible regression checks. Independent acceptance must
provide and run a separate frozen holdout before any unseen-attack claim is made. The current Phase
11 worktree has no such holdout artifact, so this decision does not itself satisfy that acceptance
requirement. Synthetic source restoration limits fixture risk but still requires disposable-stack
execution to prove cleanup and source immutability.

## Evidence

The open corpus and source-bound receipts are in `evals/phase11/` and
`apps/api/src/vehicle_platform/agent_evaluation/`. Disposable execution and final-SHA acceptance
remain pending; historical Phase 7D observations remain mixed-round and mixed-SHA.
