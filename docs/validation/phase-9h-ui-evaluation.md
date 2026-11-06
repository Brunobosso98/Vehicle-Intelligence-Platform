# Phase 9H UI evaluation

**Visual review is iterative; the final exact-head screenshots and verdict are linked from [PR #57 checks](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/57/checks).**
The latest Chromium acceptance [42252152633](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/42252152633)
passed on `ddee2eefe75ec2b91e1ee112fd35b4cd4f51cb04`; [artifact 13521557235](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/42252152633/artifacts/13521557235)
contains the corrected screenshots and metrics. The earlier clipped 9C axis labels and early overview
capture were fixed. The tablet history now uses readable labeled rows, and automated checks report no
chart-label or responsive/table overflow. The final documentation commit's screenshot artifact remains
the delivery authority.

## Screenshot captures

Desktop, tablet and mobile captures were visually reviewed from the exact-head Playwright artifact.
The page keeps the incumbent charcoal engineering style, separates the explicit demo from protected
historical reads, displays exact scores and frozen thresholds, retains accessible tables beside
chart values, and states scientific limitations next to results. Mobile stacks metadata and history
without horizontal clipping. The 9G summary is synthetic-only, offline research.

Generated PNGs are not checked into source control. The ignored local capture directory is
`.validation/phase9h/screenshots/`; the reviewed exact-head artifact is attached to
[run 42252152633](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/42252152633)
([artifact 13521557235](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/actions/runs/42252152633/artifacts/13521557235)).
The JSON measurements are in `.validation/phase9h/playwright/synthetic-ui-metrics.json` and
`.validation/phase9h/playwright/persisted-ui-metrics.json`. To reproduce the synthetic captures,
start a test-only Next.js development server with `PREDICTIVE_UI_DEMO_ENABLED=true`, then run
`PREDICTIVE_UI_DEMO_ENABLED=true PHASE9H_SCREENSHOT_DIR="$PWD/.validation/phase9h/screenshots" pnpm --filter @vehicle-platform/web exec playwright test predictive.spec.ts --project chromium -g "Phase 9H explicit synthetic UI"`.
For new persisted database-backed captures, run `make phase9h-acceptance` on a Docker-capable host.
The independent runner produced and visually reviewed these synthetic demo capture IDs:

| Capture ID                   | File                                     | State                                          |
| ---------------------------- | ---------------------------------------- | ---------------------------------------------- |
| `synthetic-operator-gate`    | `operator-gate-desktop.png`              | Explicit synthetic demo entry                  |
| `synthetic-overview`         | `synthetic-overview-desktop.png`         | Selected vehicle and scored overview           |
| `synthetic-history`          | `synthetic-history-desktop.png`          | Pull history and filters                       |
| `synthetic-anomaly`          | `synthetic-anomaly-desktop.png`          | Detector family and original threshold         |
| `synthetic-abstained`        | `synthetic-abstained-desktop.png`        | Abstained model result                         |
| `synthetic-partial-evidence` | `synthetic-partial-evidence-desktop.png` | Partial evidence and missing-data details      |
| `synthetic-research`         | `synthetic-research-desktop.png`         | Synthetic-only 9G research                     |
| `synthetic-tablet`           | `synthetic-tablet.png`                   | 768 px responsive layout                       |
| `synthetic-mobile`           | `synthetic-mobile.png`                   | 390 px responsive layout                       |
| `production-operator-gate`   | `operator-gate-production-desktop.png`   | Disabled private experience in production mode |

The exact-head runner also captured controlled persisted-read views:

| Capture ID                 | File                                     | State                                         |
| -------------------------- | ---------------------------------------- | --------------------------------------------- |
| `persisted-operator-gate`  | `persisted-operator-gate.png`            | Protected operator entry                      |
| `persisted-login-denied`   | `persisted-login-denied.png`             | Rejected unauthenticated login                |
| `persisted-overview`       | `persisted-overview-desktop.png`         | Authorized original 9D/9E history             |
| `persisted-scored-receipt` | `persisted-scored-receipt.png`           | Original score, threshold, horizon and source |
| `persisted-abstained`      | `persisted-abstained.png`                | Persisted abstained result                    |
| `proof-state-partial`      | `proof-state-partial-overlay.png`        | Source-bound partial evidence test state      |
| `proof-state-unverifiable` | `proof-state-not-verifiable-overlay.png` | Source-bound unverifiable evidence test state |
| `persisted-proof-mismatch` | `persisted-proof-mismatch.png`           | Fail-closed evidence scope mismatch           |
| `persisted-research`       | `persisted-research-desktop.png`         | 9G research with limitations                  |
| `persisted-mobile`         | `persisted-mobile.png`                   | 390 px protected-read layout                  |

The partial/unverifiable screenshots use test-only response overlays keyed to original
disposable-database receipt IDs and immutable source evidence. They prove UI wording and fail-closed
behavior; those overlay states are not claimed as persisted 9E rows.

## Browser and chart measurements

Measured by Chromium in the independent CI run (390 × 844 viewport; synthetic responsive checks
also covered 1440 px and 768 px):

| Measurement                                    |                           Result | Scope                                                     |
| ---------------------------------------------- | -------------------------------: | --------------------------------------------------------- |
| Operator entry ready                           |                         2,700 ms | Synthetic route/session readiness                         |
| Synthetic demo interactive                     |                            95 ms | After explicit demo controls became available             |
| Synthetic responsive overflow                  |     0 px at 1440, 768 and 390 px | Chromium document width                                   |
| Persisted responsive overflow                  |                   0 px at 390 px | Protected-read browser measurement                        |
| Axe violations                                 |                                0 | WCAG 2.2 AA-related tags in both modes                    |
| Browser console errors                         |                                0 | Both captured Chromium journeys                           |
| Persisted resources / browser requests         |                        101 / 102 | 390 × 844 protected-read browser run                      |
| Persisted client scripts, encoded bytes        |                 17 / 6,694,820 B | Client script count and transfer bytes                    |
| Persisted client scripts, decoded bytes        |                     29,376,593 B | Decoded client script bytes                               |
| Persisted all-resource encoded / decoded bytes |         6,943,485 / 29,628,422 B | 101 browser resources; development-harness measurement    |
| Synthetic fixture encoded / decoded bytes      |                  5,916 / 5,916 B | Explicit demo endpoint                                    |
| DOM nodes                                      |         726 persisted / 490 demo | 390 px; fixture and UI nodes included                     |
| Persisted charts                               | 3; 3 ticks, 1 point, 1 threshold | One source record per supervised task in this viewport    |
| Synthetic charts                               | 2; 3 ticks, 1 point, 1 threshold | Explicit demo fixture                                     |
| Next.js page response                          |         298 ms cold / 21 ms warm | `web.log`; development response includes cold compilation |

The bounded 500-point SVG benchmark rendered 500 points and 500 threshold marks in five jsdom
samples. Median was 109.28 ms, p95 was 126.11 ms, the chart rendered 2,521 nodes, and the
approximate heap delta was 56,155,944 bytes. This is a component-render approximation, not a
browser or production SLA. The protected-mode page transferred about 6.94 MB encoded / 29.63 MB
decoded across all resources in this development harness; this is context, not a production bundle
budget. The benchmark JSON receipt is `.validation/phase9h/playwright/chart-500-render.json`.

Playwright checked keyboard Tab focus on the skip link, history selection, abstained and partial
states, the anomaly scale and research summary. Axe reported zero violations; browser errors and
horizontal overflow were zero. The browser asserts that the synthetic demo makes zero serving
requests. No screenshot is evidence of statistical validity.

## Remaining visual evidence

| View                                                                                 | Evidence                                        | Status                                                                        |
| ------------------------------------------------------------------------------------ | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| Synthetic desktop overview, history, anomaly, abstention, partial evidence, research | Ignored Playwright artifacts; capture IDs above | PASS                                                                          |
| Synthetic 768 px tablet and 390 px mobile                                            | Ignored Playwright artifacts; capture IDs above | PASS; zero horizontal overflow                                                |
| Persisted operator, receipt, evidence and science                                    | Disposable DB + protected BFF + Chromium        | **PASS on ddee2ee**; 11 source receipts across 3 tasks and 4 anomaly families |
| Persisted axe, secret disclosure and internal API-host requests                      | Exact-head Phase 9H workflow                    | **PASS on ddee2ee**; 0 axe issues, 0 leaks, 0 internal API-host requests      |

Persisted browser parity is proven against the disposable-database oracle on implementation SHA
`ddee2eefe75ec2b91e1ee112fd35b4cd4f51cb04`; all captured fixture source roles are synthetic. Manual
review of the desktop overview, scored receipt, tablet and mobile captures found no remaining clipping
or usability issue. Exact stored-value display does not establish predictive validity or mechanical
diagnosis. The PR checks page is authoritative for the final documentation commit.
