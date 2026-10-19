# Detector card: comparable RPM performance

- **Purpose:** identify unusual completed-pull acceleration timing within comparable RPM bands.
- **Inputs:** Phase 9A elapsed seconds per 1,000 RPM, including the 3,500–4,500 RPM interval and
  adjacent intervals and pull duration.
- **Methods:** robust median/MAD baseline; bounded fixed-seed Isolation Forest candidate.
- **Score:** larger means more unusual relative timing; not an engine-power estimate or failure
  probability.
- **Missing/quality behavior:** incomplete or discontinuous RPM coverage, low quality, incompatible
  configuration/modifications or sparse history abstain.
- **Interpretation:** timing differences can reflect operating context or measurement quality. This
  detector does not infer a mechanical cause.
- **Evidence:** controlled RPM interval perturbations are in the
  [Phase 9C evaluation report](../../validation/phase-9c-model-evaluation.md).
