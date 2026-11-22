# Phase 10 pipeline and candidate evaluation

## Protocol and provenance

The disposable-database acceptance uses existing Phase 9A/9B/9C/9G paths. Runs bind the repository SHA, immutable versioned definition and fingerprint, controlled source role, exact feature/dataset fingerprints, label/oracle checksum, training/evaluation cutoff, seed, registered artifact checksum and 9G report checksum. Cohorts are temporally and entity disjoint. Candidate comparison requires the same eligible rows, task/family, horizon, schema, source role and protocol; otherwise it returns `NOT_COMPARABLE` with a reason.

On SHA `439e099f7e7c1b832db8b7f3d39be004a15f30a7`, seven candidate artifacts were registered and verified (three supervised and four anomaly families). Each has 40 training sessions; supervised training row counts are 141/158/158 and anomaly training row counts are 40 each. All artifacts are private, checksummed and loaded through existing 9B/9C serializers. Synthetic fixture labels and held-out cohorts are explicit; no missing labels or measurements are invented.

## Supervised Phase 9B results

Matched champion/challenger evaluation used identical held-out cohorts. Every metric delta was zero. These are synthetic protocol results, not real-world failure probabilities.

| Task                    | Train rows | Held-out rows | Held-out sessions | Neg/pos |  AUROC |     AP |  Brier |    ECE | Log loss | Δ all |
| ----------------------- | ---------: | ------------: | ----------------: | ------: | -----: | -----: | -----: | -----: | -------: | ----: |
| Fuel deviation          |        141 |            69 |                20 |   35/34 | 0.8088 | 0.8071 | 0.1745 | 0.0415 |   0.5200 |     0 |
| Performance degradation |        158 |            78 |                20 |   48/30 | 0.8806 | 0.7335 | 0.1525 | 0.1132 |   0.4681 |     0 |
| Thermal degradation     |        158 |            78 |                20 |   46/32 | 0.8726 | 0.7733 | 0.1145 | 0.0941 |   0.3976 |     0 |

Feature version is `phase9a-pull-v2`. Each training cohort contains 40 sessions and uses the frozen March 1, 2026 training cutoff. Evaluation pulls are after the cutoff and before the October 2, 2026 evaluation cutoff, using held-out vehicle/configuration blocks.

The receipt also binds each immutable dataset and artifact by SHA-256. All seven candidates use feature checksum `259d9fc23b29c920043990bffaf5a96407f134ca086e3ade6040b7a1a837a8ed`.

| Candidate                  | Training dataset SHA-256                                           | Evaluation dataset SHA-256                                         | Artifact SHA-256                                                   |
| -------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| 9B fuel deviation          | `cc39b9941dbff8e7a597d4f7decaae2956f7e7c50c70ff69c185c9bac8e8b7a1` | `986a71ea9c025989f0a996ed5b2f9e445f6ceab18198530d49635a2f9b045a82` | `a74520c234129cc865c3d71150653377de675c76edd3ecc9e8f684abc9dc52f8` |
| 9B performance degradation | `f15ab2afb17be764e5c1b16e7b68083fd0f0b59ec0700668d2f8fd52228376f0` | `95f1f550dc7acd57e92985c0b6bd79d2173f9a8f98da36d687e8cd9aec08d772` | `cdfa6f35f58db40fe66c1a2cb03e438bde30610681b69c7ec7a6b6bc2b0e011e` |
| 9B thermal degradation     | `49feba7c863420d3fdd0be50eb5f6cf592c7e5e776e0485cbd531857af534da8` | `7c82191e0c1def0ba945c6c05d36a234ab987e6a4047775ccaec0994ac68ea78` | `87446e7fa22f7e02feb6a3d283dbc57e4c498177dee1c0770ff8d8b8b0319424` |
| 9C boost/air               | `8b4e9dd6bf34786a3decf2f6caaf9e2a1799687e60e8ff65b48f6932bdb243ba` | `e23538185ed60249a9c51b081dd62b201a11e59bbc9005edc872c3d2cec72921` | `6f140d91659111e6f34c079e26f6289cb6623320f8cea34cff4556e6ab215281` |
| 9C fuel                    | `e8d7d226ef30a1a042343a759939de8329ed6f8865190666a9b74d94ffadd357` | `88f1bd9a480f704d8cbaa1edc29ae2d4c7b6c3cdbb7716b634da2cee839510a1` | `1c39a8b8786f36caa92b71710478c97c49ecd4602f7884bc47147a08d7215c67` |
| 9C performance             | `da8dbfe9cf3206758c72af30b1a16df97c1253ef2adf0f5a0bddc488adb137bb` | `6ee2fea864b53a20c5dd1c5973fc918b13dea29f98f60777a3fa78c8759d4fcf` | `70821b3d11925f6578e49f9aaf6e052b3a2c5894cc63052d2d4940b2460f0274` |
| 9C thermal                 | `079b54f7a3747d528356f2db30045f7da64fbee123c75edfbb56efc0b7282f21` | `536c2594ce34c4e35d5a012b46925846d1eb55dbf714d961ed809b597fe2640b` | `28fe26b3656a9e72c7cdc312f9d42faa35c868a7957c96008426f569b7582f41` |

## Phase 9C anomaly results

All families used 40 held-out rows and matched cohorts; all reported deltas were zero. Coverage is shown because detectors may abstain. Raw Robust MAD and Isolation Forest scores are not compared across scales.

| Family      | Rows |     F1 | Recall |    FPR | Scored coverage |   Δ |
| ----------- | ---: | -----: | -----: | -----: | --------------: | --: |
| boost_air   |   40 | 0.6667 | 1.0000 | 0.1333 |    34/40 (0.85) |   0 |
| fuel        |   40 | 0.6667 | 1.0000 | 0.1333 |    34/40 (0.85) |   0 |
| performance |   40 | 1.0000 | 1.0000 | 0.0000 |    34/40 (0.85) |   0 |
| thermal     |   40 | 0.5714 | 1.0000 | 0.2000 |    30/40 (0.75) |   0 |

Training support for each family is 40 rows over 8 sessions with feature version `phase9a-pull-v2`. Threshold/reference and no-reference abstention behavior remain governed by Phase 9C's frozen policy.

## Reproduction, eligibility and limits

The evaluator reconstructed a supervised candidate from its frozen training lineage in a private temporary artifact root. Artifact bytes, dataset/metrics checksums and evaluation cohort matched exactly; source rows were unchanged. The reproduced artifact was 26,689 bytes and took 6.457 seconds. Reproduction created no new run, registry row or evaluation record and did not tune against held-out labels.

Incompatible candidate/task/cohort rejection, source-role spoof rejection, temporal/source leakage checks, artifact tamper and unsafe serialization rejection, and stale artifact handling passed the independent acceptance. Every candidate retains Phase 9G readiness `SYNTHETIC_ONLY`, with production use `PROHIBITED`. Synthetic calibration is not evidence of real-world validity; supervised outputs are not mechanical failure probabilities and anomaly outputs are neither engine-health percentages nor diagnoses. Real-world mechanical failure predictive reliability remains **NOT_ESTABLISHED**.
