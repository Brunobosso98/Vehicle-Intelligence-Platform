# ADR 0007: Trunk-based development

## Status

Accepted — 2026-10-01.

## Context

A small project needs frequent integration and observable quality gates.

## Decision

main plus short-lived branches, Conventional Commits and required PR checks; document rulesets instead of destructive remote changes.

## Alternatives considered

Permanent develop/release branches; direct unrestricted main changes.

## Consequences

Review and CI protect integration. Branch protection and security settings still need repository admin configuration.
