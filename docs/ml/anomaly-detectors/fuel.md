# Detector card: fuel pressure

- **Purpose:** identify unusual recorded rail-pressure values relative to a compatible source and
  vehicle history.
- **Inputs:** canonical rail-pressure minimum, mean, delta and spread in Pa.
- **Methods:** robust median/MAD baseline; bounded fixed-seed Isolation Forest candidate.
- **Score:** larger means more unusual relative to the reference; not a fuel-system diagnosis or
  pressure safety threshold.
- **Missing/quality behavior:** if the acquisition source does not provide actual high-pressure
  telemetry, the detector is rejected or the observation abstains as unsupported/insufficient
  signal. No pressure value is inferred from other families.
- **Interpretation:** low recorded pressure is a statistical observation only. It does not establish
  sensor validity, operating condition, cause, or component risk.
- **Evidence:** controlled pressure perturbations and the explicit no-fuel-source rejection are
  reported in the [Phase 9C evaluation report](../../validation/phase-9c-model-evaluation.md).
