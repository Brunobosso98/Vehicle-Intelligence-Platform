# Phase 10 pipeline and candidate evaluation

## Protocol and provenance

The disposable-database acceptance uses existing Phase 9A/9B/9C/9G paths. Runs bind the repository SHA, immutable versioned definition and fingerprint, controlled source role, exact feature/dataset fingerprints, label/oracle checksum, training/evaluation cutoff, seed, registered artifact checksum and 9G report checksum. Cohorts are temporally and entity disjoint. Candidate comparison requires the same eligible rows, task/family, horizon, schema, source role and protocol; otherwise it returns `NOT_COMPARABLE` with a reason.

On accepted implementation SHA `c5114e07972456a9922f7d06f8c1925129adc351`, seven candidate artifacts were registered and independently verified (three supervised and four anomaly families). Each supervised training cohort has 40 sessions, with 141/158/158 rows; each anomaly cohort has 40 rows over 8 sessions. All artifacts are private, checksummed and loaded through existing 9B/9C serializers. Synthetic fixture labels and held-out cohorts are explicit; no missing labels or measurements are invented.

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
| 9B fuel deviation          | `9c50cf0c97818daada93028195e2e35f675bb17fa7185dfc58984cbe8b25e895` | `1bf9baa08b8a1eeadd1e9486392cf09edaf9f3526b1b820627b9000954f667a4` | `a74520c234129cc865c3d71150653377de675c76edd3ecc9e8f684abc9dc52f8` |
| 9B performance degradation | `31fbc26dedf5f01a86bd862b8f865b712c4ab8ef46578fa6e0d2a87d75014153` | `5fa85bf262f5648ab5033a9a6e9a472ad5c372922b7814ec44ede38c38ba69f5` | `cdfa6f35f58db40fe66c1a2cb03e438bde30610681b69c7ec7a6b6bc2b0e011e` |
| 9B thermal degradation     | `68eafcce61b1955a28f2eb9fdd848f9482f91e1fdae1f8925926664e8d263434` | `ff07c3dbaa44f33a4f9e28a1c2247eb36dcd057ab3180ad502545298d80d3f6d` | `87446e7fa22f7e02feb6a3d283dbc57e4c498177dee1c0770ff8d8b8b0319424` |
| 9C boost/air               | `9b90f5044361395fc64c284269f86fbf6503ecc83318d4fee4d1e56568a94b37` | `c56f2ae77af07110d497c0de42859327e4a883306f6ccc6666c916c435b2fac4` | `14953e8aa6c600b0801ee4c6190beda9b145ec8009fbc4f734ac472c398f36a9` |
| 9C fuel                    | `dc130dc1c79364314ba43574aea2e82b1bdfd1962dd57a99b7da3462cf0aa924` | `807a372d210ba024c1ba1a31a0ffe83d828b53ab333ffba68f386eb5d0e22a86` | `e795d1b4a625c533141a334937cb4253139e1b8dfea603d7bd4620c3e0181188` |
| 9C performance             | `52d44f8b396351b3c8006fa921a73a4b22951db3bcb1d42d36ad8f4646bafb95` | `c6a852036c69fe9171c305e6ed57b38c949403e118c711f66ba8f15872ba43d8` | `649b7769fa1fa2f2494b5f64d87f6fa0c86a14fe66671d0daa9fcb4aa25721ae` |
| 9C thermal                 | `5dab3e3932888dc1766501f6c35d2a1fcc92e704413c77fb706531a0c32ca157` | `e77c289bbedaa60dbf9982127ed06c1e0be196bab15f241d0a505c4cbf3b641a` | `6048c21687638e6081bac59dd472adf601406b71343d0203fd82d69fab26af3f` |

## Phase 9C anomaly results

All families used 40 held-out rows and matched cohorts; all reported deltas were zero. Coverage is shown because detectors may abstain. Raw Robust MAD and Isolation Forest scores are not compared across scales.

| Family      | Rows |     F1 | Recall |    FPR | Scored coverage |   Δ |
| ----------- | ---: | -----: | -----: | -----: | --------------: | --: |
| boost_air   |   40 | 0.6667 | 1.0000 | 0.1333 |    34/40 (0.85) |   0 |
| fuel        |   40 | 0.6667 | 1.0000 | 0.1333 |    34/40 (0.85) |   0 |
| performance |   40 | 1.0000 | 1.0000 | 0.0000 |    34/40 (0.85) |   0 |
| thermal     |   40 | 0.5714 | 1.0000 | 0.2000 |    30/40 (0.75) |   0 |

Training support for each family is 40 rows over 8 sessions with feature version `phase9a-pull-v2`. Threshold/reference and no-reference abstention behavior remain governed by Phase 9C's frozen policy.

## Final bounded benchmark

The exact-SHA acceptance receipt records seven pipeline runs in 436.24 seconds wall time, 235.11 CPU seconds and 986,628,096-byte peak RSS. Aggregate pipeline execution was 187.52 seconds and planning was 14.16 seconds. Eight measured artifacts, including temporary reproduction, totaled 92,256 bytes; the largest was 32,105 bytes against the configured 50 MiB limit. This is deterministic synthetic disposable-database evidence, not a production capacity claim.

## Reproduction, eligibility and limits

The evaluator reconstructed a supervised candidate from its frozen training lineage in a private temporary artifact root. Artifact bytes, dataset/metrics checksums and evaluation cohort matched exactly; source rows were unchanged. The reproduced artifact was 26,689 bytes and took 4.968 seconds. Reproduction created no new run, registry row or evaluation record and did not tune against held-out labels.

Incompatible candidate/task/cohort rejection, source-role spoof rejection, temporal/source leakage checks, artifact tamper and unsafe serialization rejection, and stale artifact handling passed the independent acceptance. Every candidate retains Phase 9G readiness `SYNTHETIC_ONLY`, with production use `PROHIBITED`. Synthetic calibration is not evidence of real-world validity; supervised outputs are not mechanical failure probabilities and anomaly outputs are neither engine-health percentages nor diagnoses. Real-world mechanical failure predictive reliability remains **NOT_ESTABLISHED**.
