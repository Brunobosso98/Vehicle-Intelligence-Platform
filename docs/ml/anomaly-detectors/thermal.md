# Detector card: thermal behavior

- **Purpose:** identify unusual thermal features relative to a compatible same-vehicle historical
  reference after a completed pull.
- **Inputs:** `thermal.iat_start`, `thermal.iat_delta_k`, `thermal.iat_slope_k_per_s`,
  `thermal.iat_recovery_delta_k`, and optional pre-pull IAT context.
- **Methods:** robust median/MAD baseline; bounded fixed-seed Isolation Forest candidate.
- **Score:** larger means a more unusual relative deviation; never a temperature safety limit or
  fault probability.
- **Missing/quality behavior:** missing required IAT, invalid values, low coverage, duplicated
  timestamps or incompatible context abstain.
- **Interpretation:** associated statistical deviation, not root cause. A seasonal or heat-soak
  context shift requires comparable historical observations; the model does not establish a cause.
- **Evidence:** controlled thermal-only injections and clean/confounder controls are in the
  [Phase 9C evaluation report](../../validation/phase-9c-model-evaluation.md).
