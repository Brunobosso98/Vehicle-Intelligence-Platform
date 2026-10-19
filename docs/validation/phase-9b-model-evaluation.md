# Phase 9B model evaluation

## Evaluation protocol

This report includes all candidate families. It uses `ENGINEERING_VALIDATION` synthetic evidence
from the same controlled Phase 9B acceptance run described in the
[acceptance report](phase-9b-acceptance.md). It is not real-world model validation.

For every task, candidate fitting and preprocessing used only the chronological training groups.
Validation AP was the primary candidate comparison; validation F1 and balanced accuracy were
predeclared floors. Thresholds were selected on validation only. Near ties favor the simpler family.
The final test partition was inspected only after selecting the family and threshold; only the
selected family and dummy baseline were scored there. Test evidence did not tune either choice.

## Candidate comparison

AP is average precision; BA is balanced accuracy. Dummy F1/precision are undefined because the
dummy predicted no positive cases at the selected threshold.

| Task        | Family              | Validation AP | Validation F1 | Validation BA | Selection                |
| ----------- | ------------------- | ------------: | ------------: | ------------: | ------------------------ |
| Thermal     | Dummy               |         0.406 |     undefined |         0.500 | baseline                 |
| Thermal     | Logistic regression |         0.609 |         0.769 |         0.806 | eligible                 |
| Thermal     | Random forest       |         0.855 |         0.769 |         0.806 | selected, threshold 0.50 |
| Performance | Dummy               |         0.344 |     undefined |         0.500 | baseline                 |
| Performance | Logistic regression |         0.773 |         0.786 |         0.857 | selected, threshold 0.45 |
| Performance | Random forest       |         0.749 |         0.762 |         0.816 | eligible                 |
| Fuel        | Dummy               |         0.500 |     undefined |         0.500 | baseline                 |
| Fuel        | Logistic regression |         0.761 |         0.720 |         0.750 | eligible                 |
| Fuel        | Random forest       |         0.889 |         0.828 |         0.821 | selected, threshold 0.40 |

All tasks met their predeclared validation and support criteria. Performance selected logistic
regression by validation AP; thermal and fuel selected random forest. This describes the controlled
fixture only.

## Held test and generalization evidence

| Task        | Partition              |    AP |        F1 |    BA | Rows / class support         |
| ----------- | ---------------------- | ----: | --------: | ----: | ---------------------------- |
| Thermal     | Test, selected         | 0.885 |     0.786 | 0.810 | 32; 18 negative, 14 positive |
| Thermal     | Test, dummy            | 0.438 | undefined | 0.500 | 32; 18 negative, 14 positive |
| Thermal     | Scenario holdout       | 0.872 |     0.720 | 0.766 | 64                           |
| Thermal     | Held-out vehicle       | 0.826 |     0.737 | 0.753 | 20                           |
| Thermal     | Held-out configuration | 0.698 |     0.836 | 0.858 | 64                           |
| Performance | Test, selected         | 0.788 |     0.643 | 0.745 | 32; 22 negative, 10 positive |
| Performance | Test, dummy            | 0.312 | undefined | 0.500 | 32; 22 negative, 10 positive |
| Performance | Scenario holdout       | 0.855 |     0.677 | 0.767 | 64                           |
| Performance | Held-out vehicle       | 0.931 |     0.737 | 0.771 | 20                           |
| Performance | Held-out configuration | 0.789 |     0.680 | 0.792 | 64                           |
| Fuel        | Test, selected         | 0.889 |     0.759 | 0.776 | 30; 17 negative, 13 positive |
| Fuel        | Test, dummy            | 0.433 | undefined | 0.500 | 30; 17 negative, 13 positive |
| Fuel        | Scenario holdout       | 0.761 |     0.692 | 0.720 | 58                           |
| Fuel        | Held-out vehicle       | 0.882 |     0.714 | 0.792 | 18                           |
| Fuel        | Held-out configuration | 0.752 |     0.700 | 0.682 | 56                           |

Performance test F1 (0.643) is lower than validation F1 (0.786), while the vehicle holdout is
0.737. The predeclared gate is an engineering fixture check, not a deployment gate. Reviewers should
retain the lower test score when assessing later work.

The active negative control is `quality.duplicate_timestamp_count`. Its validation permutation
importance share was 0.8% thermal, 2.7% performance and 2.4% fuel. The acceptance gate rejects a
control with at least 50% of total importance. Performance also uses current-pull
`quality.sample_interval_stddev_s` as a timing input; it is distinct from the irrelevant control.

Each task also ran three expanding walk-forward folds. Fold supports are small and several fold
metrics are undefined or marked `INSUFFICIENT_TEST_SUPPORT`. Fold results, reliability summaries,
confusion matrices, feature associations and all hyperparameters are retained in the ignored
machine-readable `.validation/phase9b/acceptance.json` generated by the acceptance command.

## Reproducibility and limits

Repeated training matched split row IDs, selected family, metrics and predictions within `1e-12`.
Artifact bytes are not asserted deterministic. Selection is based on fixed seeded candidates,
scikit-learn `1.9.1`, one-thread numerical execution and a recorded feature/label/spec checksum.

The fixture is controlled and synthetic, with 8 vehicles, 16 configurations, 40 sessions and 200
pulls. These small sample counts, generated relationships and repeated sessions cannot establish
real sensor behavior, independent fleet generalization, probability calibration or component
failure prediction. No mechanical failures were labeled.
