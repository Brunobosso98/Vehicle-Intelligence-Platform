# ADR 0032: Versioned next-pull outcome labels

Status: accepted for Phase 9B.

## Context

Phase 9B needs supervised labels for behavior with no validated component-failure ground truth.
The label must be reconstructable from canonical future observations while keeping target-pull
measurements out of the input feature vector. A missing or incompatible immediate next pull must
not silently become a later target.

## Decision

Define three binary, versioned `NEXT_PULL` engineering outcomes: relative thermal degradation,
relative 3,500–4,500 RPM interval slowdown, and fuel-pressure deviation from compatible prior
history. Persist a label-definition checksum and target pull/session/configuration, outcome window,
values, quality, algorithm version and source hash. Build input and outcome snapshots separately
using the Phase 9A availability/cutoff contract. Pair only the immediate next candidate pull with
the same vehicle, effective configuration and compatible modifications. Preserve bounded
exclusion reasons for missing, impaired and incompatible targets.

The thresholds are explicit engineering validation rules, not OEM limits or failure diagnosis.
Changing a rule creates a new label version. No documentary knowledge supplies measurements.

## Consequences

- Supervised labels are reproducible and auditable to source outcome records.
- A missing sensor reduces support and may prevent a task from training.
- The three tasks can later be revised independently without mutating historical labels.
- Synthetic acceptance can establish pipeline behavior, not real-world predictive validity.

## Alternatives considered

- **Skip an unusable next pull and label a later pull:** rejected because it changes the declared
  horizon and can select outcomes based on availability.
- **Use component-failure or maintenance labels:** rejected until validated real labels exist.
- **Infer absent pressure or temperature from manuals/RAG:** rejected because documentary values
  are not measurements.
