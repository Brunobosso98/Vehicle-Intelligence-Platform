# Phase 9C detector cards

These cards describe local controlled engineering evaluation of four independent offline detector
families. Each family has a `robust_mad` baseline and an `isolation_forest` candidate. Per-family
validation selection and final held-out metrics are recorded in the [evaluation report](../../validation/phase-9c-model-evaluation.md).

| Card                                     | Canonical feature scope                                   | Source limitation                                              |
| ---------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| [Thermal behavior](thermal.md)           | IAT start/context, delta, slope and recovery              | Requires compatible intake temperature history                 |
| [Boost and air behavior](boost-air.md)   | Mean/peak pressure, rise, spread and historical deviation | Requires pressure samples and compatible vehicle configuration |
| [Comparable performance](performance.md) | Fixed 3,500–4,500 RPM interval and adjacent RPM bands     | Requires continuous comparable RPM coverage                    |
| [Fuel pressure](fuel.md)                 | Rail-pressure minimum, mean, delta and spread             | Not evaluated when actual pressure telemetry is unavailable    |

All scores are relative engineering deviations. A finding is not a mechanical diagnosis, root-cause
claim, failure probability, OEM safety limit, maintenance order or universal cross-car comparison.
The cards and synthetic acceptance do not establish real-vehicle accuracy or fleet generalization.
