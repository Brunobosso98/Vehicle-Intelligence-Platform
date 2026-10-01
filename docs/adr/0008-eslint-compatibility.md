# ADR 0008: ESLint 10 compatibility bridge

## Status

Accepted — 2026-10-01.

## Context

Registry ESLint 9 is deprecated; Next plugins still declare ESLint <=9 and call removed context APIs.

## Decision

Use current ESLint 10 and official @eslint/compat fixupConfigRules for released Next configs. Narrow peer compatibility rules acknowledge that bridge for the three exact plugin versions, after running lint and tests.

## Alternatives considered

Deprecated ESLint 9; dropping React/accessibility rules; disabling failing rules.

## Consequences

The bridge is tooling-only, preserves rules and must be removed when upstream plugins support ESLint 10. Pin all versions; future upgrades must revalidate plugin compatibility.
