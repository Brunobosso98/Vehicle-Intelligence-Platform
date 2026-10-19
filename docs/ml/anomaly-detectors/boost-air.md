# Detector card: boost and air behavior

- **Purpose:** identify unusual boost/air behavior relative to compatible same-vehicle history.
- **Version:** `2.0.0`; this version uses within-pull mean and peak pressure, rise rate and spread.
- **Inputs:** canonical within-pull pressure mean and peak, rise rate and spread in Pa and Pa/s.
- **Excluded input:** `boost_air.history_deviation_pa` is a rolling comparison to earlier pulls.
  Its value depends on recent history and can change after a rare prior pull even when current
  pressure returns to its usual range. It remains a Phase 9A feature, but this detector does not
  compare that second-order feature against its own historical distribution.
- **Methods:** robust median/MAD baseline; bounded fixed-seed Isolation Forest candidate.
- **Score:** larger means more unusual; not an underboost/overboost diagnosis or probability.
- **Missing/quality behavior:** required pressure capability, valid units and eligible reference
  support are necessary. Missing signals or incompatible vehicle/configuration context abstain.
- **Interpretation:** a pressure deviation is an associated statistical difference. It does not
  establish whether the engine, sensor, calibration, environment or driver caused it.
- **Evidence:** controlled boost-only cases are reported separately from performance cases in the
  [Phase 9C evaluation report](../../validation/phase-9c-model-evaluation.md).
