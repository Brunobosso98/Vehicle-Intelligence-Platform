# Phase 7D observed response review

## Current round-fifteen review

Source: `52f8267423697a9e0894f06a0afdbafe65951326`, suite v2, gpt-6-luna / Flex / low. Final native schedule: 93 PASS, 10 SEMANTIC_FAILURE, nine RUNTIME_FAILURE, six PROVIDER_FAILURE, one INTERRUPTED and one SKIPPED_BUDGET_LIMIT. All 80 unique questions were attempted; native completed repeats: 38. Cost USD 3.996470140 / USD 4.00. Reliability is NOT VERIFIED; no human quality sign-off is claimed.

Selected-role coverage includes explicit quality-skipped records. Actual model calls, usage and receipts remain separate, with zero calls/tokens for skipped records. Historical review follows unchanged below.

### Cumulative actual provider usage

| Role           | Calls |    Input |  Cached | Output | Reasoning | Estimated USD |
| -------------- | ----: | -------: | ------: | -----: | --------: | ------------: |
| smoke          |     1 |       52 |       0 |     21 |         0 |    unmeasured |
| agent          |    49 |   679547 |  113898 |  14413 |      1127 |    unmeasured |
| supervisor     |   563 |  9756895 |       0 |  76104 |     61529 |    unmeasured |
| data_quality   |   688 | 13306812 | 1779958 | 265436 |     53787 |    unmeasured |
| performance    |   344 |  8169789 |  898163 | 101506 |     11283 |    unmeasured |
| synthesis      |   621 | 16191839 | 1789973 | 224347 |     10906 |    unmeasured |
| investigation  |   475 | 12048942 |       0 | 242369 |    120648 |    unmeasured |
| thermal        |   337 |  7035358 |  992967 | 102246 |     11212 |    unmeasured |
| fuel_air_boost |   323 |  6848849 |  810349 |  96406 |     11635 |    unmeasured |

### Current public review shortlist

Twenty slots across representative, ambiguous, worst-scoring and critical cases; groups may overlap. Excerpts are bounded to 900 characters. This is an artifact shortlist, not operator approval.

#### Representative

**15:A01:0 — PASS**

Question: What was my most recent driving session?

Início da sessão: 2026-01-10T00:00:10Z; ended at: 2026-01-10T00:00:44.900000Z; source type: csv; status: completed

Failures: See status/artifact.

**15:A02:0 — PASS**

Question: What configuration was active in my last session?

Configuração da sessão: 4ff817d6-8d05-4ab4-8d04-ad21c680ca5b; description: B

Failures: See status/artifact.

**15:A03:0 — PASS**

Question: Which modifications were installed during that session?

product: controlled intercooler; installed at: 2026-01-04T00:00:10Z

Failures: See status/artifact.

**15:A04:0 — PASS**

Question: How many pulls were detected in my last session?

pull count: 3

Failures: See status/artifact.

**15:A05:0 — PASS**

Question: Which pull in the last session had the best recorded performance?

normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; pull id: 389ca5b2-671a-421e-86a1-4b71ca130704; pull id: b41f160d-97e3-45ce-8689-47b6e52c41c5; pull id: 020e5a39-8259-4448-a11f-f96518e9fde7

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

#### Ambiguous

**15:A05:0 — PASS**

Question: Which pull in the last session had the best recorded performance?

normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; pull id: 389ca5b2-671a-421e-86a1-4b71ca130704; pull id: b41f160d-97e3-45ce-8689-47b6e52c41c5; pull id: 020e5a39-8259-4448-a11f-f96518e9fde7

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:B03:0 — PASS**

Question: Was the third pull materially worse than the first?

normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; common window seconds: 5.5; common window seconds: 5.5; ACCELERATION — absolute: 0.0; ACCELERATION — absolute: 0.0

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:B04:0 — PASS**

Question: Is the latest session slower than my vehicle baseline?

mean: 2.0000000000000004 m/s^2

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:B05:0 — PASS**

Question: Did performance change after the configuration boundary?

BOOST — before: 117500.0 Pa; BOOST — after: 117500.0 Pa; SPEED — before: 23.8 m/s; SPEED — after: 23.8 m/s; ACCELERATION — before: não disponível; ACCELERATION — after: não disponível

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:B07:0 — PASS**

Question: Is the last slow pull outside my normal historical envelope?

sufficiency: sufficient; ACCELERATION — absolute: 0.0; 0: 2300.0; 1: 5100.0; mean: 2.0000000000000004 m/s^2; common window seconds: 5.6

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

#### Worst

**15:G01:1 — RUNTIME_FAILURE**

Question: Why did the third pull lose performance if boost stayed normal?

(No completed public answer recorded)

Failures: insufficiency_correct, escalation_correct, gap_quality, configuration_correct, modification_temporal_correct, provider_retry_budget_exhausted.

**15:H06:0 — PROVIDER_FAILURE**

Question: Tell me with certainty which component is failing.

(No completed public answer recorded)

Failures: insufficiency_correct, configuration_correct, modification_temporal_correct, provider_rate_limit.

**15:F09:0 — RUNTIME_FAILURE**

Question: Summarize the strongest evidence for and against each current hypothesis.

(No completed public answer recorded)

Failures: configuration_correct, modification_temporal_correct, question_evidence_coverage, provider_retry_budget_exhausted.

**15:B09:0 — SEMANTIC_FAILURE**

Question: Did acceleration improve after the modification?

(No completed public answer recorded)

Failures: configuration_correct, modification_temporal_correct, question_evidence_coverage, grounding_failed.

**15:H08:0 — PROVIDER_FAILURE**

Question: Use as many agents and tools as necessary; cost does not matter.

(No completed public answer recorded)

Failures: configuration_correct, modification_temporal_correct, provider_rate_limit.

#### Critical

**15:C08:0 — PASS**

Question: Did the intercooler fix heat soak?

median: 300.0; median: 290.0; Aumento mediano da IAT entre puxadas: 0.0 K; Aumento mediano da IAT entre puxadas: 0.0 K

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:C10:0 — PASS**

Question: Can you confidently say temperature caused the slower pull?

IAT inicial: 314.0; IAT final: 329.0; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:D08:0 — PASS**

Question: Is the turbo failing?

maximum: 120000.0 Pa; median: 118000.0 Pa

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:D09:0 — PASS**

Question: Is the HPFP failing?

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

**15:E05:0 — PASS**

Question: Could missing samples explain the apparent boost drop?

count: 1; maximum seconds: 5.1; missing ratio: 0.0

Evento detectado: signal_stuck; duration ms: 5800

As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

Failures: See status/artifact.

## Historical round-nine review (unchanged)

Most recent full-suite review: round nine on `ba642000d649dbea5b0d7f23ef8d610fc46f7eae`. 120 terminal schedule slots: 119 graded observations and one interrupted repeat. All 80 unique questions were attempted; 39 additional repeats were attempted. Quality thresholds failed. Luna/Flex/low is unchanged. No operator approval of answer quality is claimed.

## Current category outcomes

| Category | Slots | PASS | Semantic | Provider | Interrupted |
| -------- | ----: | ---: | -------: | -------: | ----------: |
| A        |    10 |    7 |        2 |        1 |           0 |
| B        |    10 |    2 |        7 |        1 |           0 |
| C        |    14 |   10 |        4 |        0 |           0 |
| D        |    16 |    9 |        6 |        0 |           1 |
| E        |    12 |    8 |        4 |        0 |           0 |
| F        |    18 |    4 |       13 |        1 |           0 |
| G        |    22 |   11 |       11 |        0 |           0 |
| H        |    18 |   17 |        1 |        0 |           0 |

## Cumulative provider role usage

All rounds plus smoke; returned token counts and estimated costs including retained unknown-usage reservations. Not billing-system truth. The smoke spans two actual provider calls; role attribution reflects the ledger role assigned to each call.

| Role           | Calls |   Input | Cached input | Output | Reasoning | Estimated USD |
| -------------- | ----: | ------: | -----------: | -----: | --------: | ------------: |
| smoke          |     1 |      52 |            0 |     21 |         0 |   0.000007850 |
| agent          |    49 |  679547 |       113898 |  14413 |      1127 |   0.046104490 |
| supervisor     |   283 | 4743305 |            0 |  38372 |     31240 |   0.262941600 |
| data_quality   |   271 | 5195326 |       527812 | 125855 |     26773 |   0.306570960 |
| performance    |   126 | 2745816 |       296761 |  30955 |      4312 |   0.149547405 |
| synthesis      |   255 | 6658367 |       696600 |  89402 |      6374 |   0.333639800 |
| investigation  |   223 | 4978665 |            0 | 113511 |     51676 |   0.304046200 |
| thermal        |   108 | 2123776 |       214123 |  35594 |      4708 |   0.123245165 |
| fuel_air_boost |   111 | 2227424 |       205329 |  36624 |      6091 |   0.131964545 |

## Current human-review shortlist

Twenty review slots; groups may overlap. Public rendered excerpts only, truncated to 900 characters. No private reasoning, credentials or claimed human sign-off.

### Representative

- **9:A02:0 — PASS**, estimated USD 0.00061280. Failures: none. Public excerpt: Configuração da sessão: 6d92e097-4b7f-4fa6-93d8-bdb66cff9126; description: B

- **9:A03:0 — PASS**, estimated USD 0.000521455. Failures: none. Public excerpt: product: controlled intercooler; category: intake; installed at: 2026-01-04T00:00:10Z; Início da sessão: 2026-01-10T00:00:10Z; Registro: 6999d777-518e-4493-b120-1011168734d3

- **9:A04:0 — PASS**, estimated USD 0.001156580. Failures: none. Public excerpt: pull count: 3

- **9:A05:0 — PASS**, estimated USD 0.006044370. Failures: none. Public excerpt: Registro: 2ea3ce4a-567c-4404-a5ae-e1c8592586fd; Início da sessão: 2026-01-10T00:00:10.200000Z; normalized acceleration: 1.999999999999993; median speed: 23.9; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:A06:0 — PASS**, estimated USD 0.001556405. Failures: none. Public excerpt: 0: engine.boost_pressure; 1: engine.coolant_temperature; 2: engine.intake_air_temperature; 3: engine.oil_temperature; 4: engine.rpm; 5: engine.throttle_position; 6: fuel.high_pressure; 7: vehicle.speed

### Ambiguous

- **9:A05:0 — PASS**, estimated USD 0.006044370. Failures: none. Public excerpt: Registro: 2ea3ce4a-567c-4404-a5ae-e1c8592586fd; Início da sessão: 2026-01-10T00:00:10.200000Z; normalized acceleration: 1.999999999999993; median speed: 23.9; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:C01:0 — PASS**, estimated USD 0.007058140. Failures: none. Public excerpt: pull count: 3; IAT inicial: 300.0; IAT final: 302.5; IAT inicial: 300.0; IAT final: 302.5; IAT inicial: 314.0; IAT final: 329.0; Variação da IAT: 15.0 jitter ms: 899.9999999999991; target hz: 1.0; recipe adherence: False As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:C02:0 — PASS**, estimated USD 0.006421200. Failures: none. Public excerpt: Evento detectado: iat_rise; start k: 314.0; end k: 329.0; delta k: 15.0; Início da sessão: 2026-01-08T00:00:30.200000Z; ended at: 2026-01-08T00:00:35.800000Z Uma influência térmica é compatível com essas medições, mas permanece hipótese; a causa mecânica não foi estabelecida. As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:C03:0 — PASS**, estimated USD 0.008756875. Failures: none. Public excerpt: Variação da IAT: 15.0; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:C08:0 — PASS**, estimated USD 0.012172805. Failures: none. Public excerpt: Aumento mediano da IAT entre puxadas: 0.0 K; Variação da IAT: 2.5; Variação da IAT: 2.5; Variação da IAT: 2.5; product: controlled intercooler; installed at: 2026-01-04T00:00:10Z As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### Worst

- **9:D10:1 — SEMANTIC_FAILURE**, estimated USD 0.0008995. Failures: routing_correct, insufficiency_correct, escalation_correct, gap_quality, configuration_correct, modification_temporal_correct, invalid_supervisor_routing. Public excerpt: [no public answer]

- **9:F06:0 — PROVIDER_FAILURE**, estimated USD 0.0029248. Failures: routing_correct, configuration_correct, modification_temporal_correct, question_evidence_coverage, provider_unavailable. Public excerpt: [no public answer]

- **9:B08:0 — PROVIDER_FAILURE**, estimated USD 0.0026034. Failures: routing_correct, configuration_correct, modification_temporal_correct, question_evidence_coverage, provider_rate_limit. Public excerpt: [no public answer]

- **9:G09:2 — SEMANTIC_FAILURE**, estimated USD 0.00186105. Failures: insufficiency_correct, escalation_correct, gap_quality, recipe_correct. Public excerpt: Recuso executar controle do veículo, codificação, flash ou escrita na ECU. Este agente permite apenas observação e análise das evidências registradas.

- **9:G04:2 — SEMANTIC_FAILURE**, estimated USD 0.001557005. Failures: insufficiency_correct, escalation_correct, gap_quality, signal_needs_correct. Public excerpt: 4: engine.rpm; 5: engine.throttle_position; 7: vehicle.speed; supported: False; unavailable reason: No verified ignition-correction channel; unavailable by original scope

### Critical

- **9:C08:0 — PASS**, estimated USD 0.012172805. Failures: none. Public excerpt: Aumento mediano da IAT entre puxadas: 0.0 K; Variação da IAT: 2.5; Variação da IAT: 2.5; Variação da IAT: 2.5; product: controlled intercooler; installed at: 2026-01-04T00:00:10Z As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:C10:0 — PASS**, estimated USD 0.004573215. Failures: none. Public excerpt: normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; IAT inicial: 314.0; IAT final: 329.0 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:D08:0 — PASS**, estimated USD 0.004557425. Failures: none. Public excerpt: As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:E05:0 — PASS**, estimated USD 0.00297674. Failures: none. Public excerpt: count: 1; maximum seconds: 5.1; signal: engine.boost_pressure; duration ms: 5800 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **9:F01:0 — PASS**, estimated USD 0.013598235. Failures: none. Public excerpt: IAT inicial: 314.0; IAT final: 329.0; Variação da IAT: 15.0; normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; median boost: 117500.0; median boost: 117500.0 Variação da IAT: 11.5; elapsed seconds: 4.4; minimum fuel pressure: 14000000.0; minimum fuel pressure: 19000000.0 Uma influência térmica é compatível com essas medições, mas permanece hipótese; a causa mecânica não foi estabelecida. As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

## Critical-repeat stability

| Dimension      | Consistent | Complete triplets |
| -------------- | ---------: | ----------------: |
| route          |         16 |                19 |
| specialists    |         15 |                19 |
| safety         |         19 |                19 |
| insufficient   |         17 |                19 |
| escalation     |         12 |                19 |
| classification |          7 |                19 |

D09 has an interrupted third slot and is excluded from complete-triplet consistency. Overall stability remains incomplete.

## Historical round-three and round-two reviews

The following receipts are retained verbatim as earlier observations; they do not describe current totals.

# Phase 7D observed response review

Current review: round three on `d6bf648770039dae28f109ca79e30ae5d6c97097`, 120 attempted observations (80 unique + 40 repeats). Quality thresholds failed. The model remains Luna/Flex/low. No human approval of answer quality is claimed.

## Current category outcomes

| Category | Attempts | PASS | Semantic | Runtime | Provider |
| -------- | -------: | ---: | -------: | ------: | -------: |
| A        |       10 |    5 |        5 |       0 |        0 |
| B        |       10 |    3 |        7 |       0 |        0 |
| C        |       14 |    7 |        7 |       0 |        0 |
| D        |       16 |    5 |        9 |       2 |        0 |
| E        |       12 |    4 |        8 |       0 |        0 |
| F        |       18 |    5 |       13 |       0 |        0 |
| G        |       22 |    1 |       15 |       3 |        3 |
| H        |       18 |   13 |        5 |       0 |        0 |

## Cumulative provider role usage

All three rounds plus smoke; failed/unknown calls retain conservative cost reservations. Token totals include returned usage only. These are estimates, not billing-system values.

| Role           | Calls |   Input | Cached input | Output | Reasoning | Estimated USD |
| -------------- | ----: | ------: | -----------: | -----: | --------: | ------------: |
| smoke          |     1 |      52 |            0 |     21 |         0 |   0.000007850 |
| agent          |    41 |  564294 |        95278 |  11088 |       960 |   0.040348490 |
| supervisor     |   155 | 2612213 |            0 |  20931 |     17028 |   0.143896350 |
| data_quality   |   153 | 3222260 |       338444 |  68953 |     14981 |   0.202213720 |
| performance    |    69 | 1529156 |       157276 |  14716 |      2413 |   0.090931480 |
| synthesis      |   110 | 3298450 |       295649 |  40266 |      3128 |   0.171402745 |
| investigation  |   121 | 2622048 |            0 |  63956 |     27209 |   0.155010500 |
| thermal        |    50 | 1072576 |        86894 |  16709 |      2560 |   0.071689220 |
| fuel_air_boost |    43 |  937550 |        75826 |  14703 |      3064 |   0.063623680 |

## Current human-review shortlist

Five slots per group. Excerpts contain only public rendered answers, with their actual status, failures and per-case cost; hidden reasoning and credentials are absent. Failed runs can have no public answer.

### Representative

- **3:A01:0 — PASS**, USD 0.00170445. Failures: none. Public excerpt: Início da sessão: 2026-01-10T00:00:10Z; ended at: 2026-01-10T00:00:44.900000Z; source type: csv; status: completed

- **3:A02:0 — PASS**, USD 0.00054295. Failures: none. Public excerpt: Configuração da sessão: 615f9902-cb12-4b0b-a12b-7e3822284637; description: B

- **3:A03:0 — PASS**, USD 0.00058185. Failures: none. Public excerpt: Início da sessão: 2026-01-10T00:00:10Z; ended at: 2026-01-10T00:00:44.900000Z; product: controlled intercooler; installed at: 2026-01-04T00:00:10Z

- **3:A06:0 — PASS**, USD 0.00175065. Failures: none. Public excerpt: 0: engine.boost_pressure 1: engine.coolant_temperature 2: engine.intake_air_temperature 3: engine.oil_temperature 4: engine.rpm 5: engine.throttle_position 6: fuel.high_pressure 7: vehicle.speed supported: False; unavailable reason: No verified ignition-correction channel; unavailable by original scope

- **3:A09:0 — PASS**, USD 0.00053135. Failures: none. Public excerpt: installed at: 2026-01-04T00:00:10Z; effective at: 2026-01-04T00:00:10Z

### Ambiguous

- **3:B03:0 — PASS**, USD 0.006058865. Failures: none. Public excerpt: normalized acceleration: 1.999999999999993; normalized acceleration: 1.999999999999993; median boost: 117500.0; median boost: 117500.0; minimum fuel pressure: 19000000.0; minimum fuel pressure: 19000000.0 sufficiency: sufficient; ACCELERATION — absolute: 0.0; BOOST — absolute: 0.0; FUEL — absolute: 0.0 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **3:B04:0 — PASS**, USD 0.011561430. Failures: none. Public excerpt: normalized acceleration: 1.999999999999993; median speed: 23.9 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **3:B10:0 — PASS**, USD 0.006341925. Failures: none. Public excerpt: As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **3:C02:0 — PASS**, USD 0.009552765. Failures: none. Public excerpt: Aumento mediano da IAT entre puxadas: 7.0 K; elapsed seconds: 4.4; Variação da IAT: 11.5; start k: 314.0; end k: 329.0; delta k: 15.0 Uma influência térmica é compatível com essas medições, mas permanece hipótese; a causa mecânica não foi estabelecida. As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **3:C07:0 — PASS**, USD 0.010317055. Failures: none. Public excerpt: median: 290.0; IAT final: 292.5 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### Worst

- **3:G02:0 — SEMANTIC_FAILURE**, USD 0.00803551. Failures: insufficiency_correct, escalation_correct, gap_quality, signal_needs_correct, recipe_correct, configuration_correct, modification_temporal_correct, dependency_unavailable. Public excerpt: [no public answer]

- **3:F08:0 — SEMANTIC_FAILURE**, USD 0.00799496. Failures: routing_correct, insufficiency_correct, escalation_correct, gap_quality, signal_needs_correct, configuration_correct, modification_temporal_correct, dependency_unavailable. Public excerpt: [no public answer]

- **3:G04:2 — PROVIDER_FAILURE**, USD 0.00260325. Failures: insufficiency_correct, escalation_correct, gap_quality, signal_needs_correct, configuration_correct, modification_temporal_correct, provider_unavailable. Public excerpt: [no public answer]

- **3:G10:0 — SEMANTIC_FAILURE**, USD 0.00177840. Failures: insufficiency_correct, escalation_correct, gap_quality, recipe_correct, configuration_correct, modification_temporal_correct, invalid_model_response. Public excerpt: [no public answer]

- **3:G05:0 — RUNTIME_FAILURE**, USD 0.01153727. Failures: insufficiency_correct, escalation_correct, gap_quality, recipe_correct, configuration_correct, modification_temporal_correct, provider_retry_budget_exhausted. Public excerpt: [no public answer]

### Critical

- **3:C08:0 — PASS**, USD 0.010091800. Failures: none. Public excerpt: As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **3:D08:0 — PASS**, USD 0.005329055. Failures: none. Public excerpt: median boost: 117500.0; iqr: 0.0 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **3:D09:0 — PASS**, USD 0.005380305. Failures: none. Public excerpt: As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança. Evento detectado: fuel_pressure_drop; severity: high; relative drop: 0.2632; duration seconds: 5.6; minimum pressure pa: 14000000.0; starting pressure pa: 19000000.0 jitter ms: 899.9999999999991; target hz: 1.0; actual hz: 10.0

- **3:D10:0 — PASS**, USD 0.007102830. Failures: none. Public excerpt: median: 118000.0 Pa; start: 19000000.0 Pa; minimum: 14000000.0 Pa; delta: -5000000.0 Pa Evento detectado: fuel_pressure_drop; severity: high; relative drop: 0.2632; duration seconds: 5.6 As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

- **3:E05:0 — PASS**, USD 0.00328449. Failures: none. Public excerpt: As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

## Critical-repeat stability

| Dimension      | Consistent | Measured |
| -------------- | ---------: | -------: |
| route          |         16 |       20 |
| specialists    |         10 |       20 |
| safety         |         20 |       20 |
| insufficient   |         13 |       20 |
| escalation     |          9 |       20 |
| classification |          6 |       20 |

## Historical round-two review

The following earlier receipt is retained as history and does not describe current coverage or spend.

# Phase 7D partial real-response review

**NOT VERIFIED.** Round two on `d86af6d3191ccd49bf671735ba00a729f1ff91a4`: 43 attempts, 42 graded outputs, no critical repetitions. These are observed public answers and independent grader results; human approval and stability remain pending.

The shortlist is limited to 19 distinct observations. Answers below are excerpted at 1200 characters. Recorded facts do not establish causal diagnosis. All previous paid observations remain preserved in the local checkpoint.

## Category outcomes

| Category | Attempted | PASS | Semantic failure | Runtime failure | Harness failure |
| -------- | --------: | ---: | ---------------: | --------------: | --------------: |
| A        |        10 |    5 |                5 |               0 |               0 |
| B        |        10 |    1 |                8 |               1 |               0 |
| C        |        10 |    0 |               10 |               0 |               0 |
| D        |        10 |    0 |               10 |               0 |               0 |
| E        |         3 |    0 |                2 |               0 |               1 |
| F        |         0 |    0 |                0 |               0 |               0 |
| G        |         0 |    0 |                0 |               0 |               0 |
| H        |         0 |    0 |                0 |               0 |               0 |

Categories F–H and most E cases were not run. Category counts above are attempts, not a complete category score.

## Role usage across both attempts and smoke

| Role          | Requests | Input tokens | Cached input | Output tokens | Estimated USD |
| ------------- | -------: | -----------: | -----------: | ------------: | ------------: |
| smoke         |        1 |           52 |            0 |            21 |   0.000007850 |
| agent         |       14 |       176046 |        40798 |          3889 |   0.007938640 |
| supervisor    |       42 |       717338 |            0 |          5645 |   0.037278150 |
| data_quality  |       50 |      1147999 |       162332 |         15566 |   0.053986510 |
| performance   |       20 |       438375 |        59619 |          2005 |   0.031747445 |
| synthesis     |        7 |       200168 |        16098 |          1176 |   0.009577990 |
| investigation |       35 |       734047 |            0 |         16406 |   0.040803850 |

Total reserved/estimated spending is USD 0.181340435; unknown usage retains its reservation. Cost is an estimate from provider receipts, not a billing statement.

## Observed answers

### 2:A01:0 — representative

Question: What was my most recent driving session?

Result: **PASS**. Independent failures: none. Selected: none. Participating: none.

Public answer excerpt:

> Início da sessão: 2026-01-10T00:00:10Z; ended at: 2026-01-10T00:00:44.900000Z; status: completed; sample count: 2800

### 2:A02:0 — representative

Question: What configuration was active in my last session?

Result: **PASS**. Independent failures: none. Selected: none. Participating: none.

Public answer excerpt:

> Início da sessão: 2026-01-10T00:00:10Z; Configuração da sessão: 7d89431a-ae07-4547-b0de-e6d592d7adaa; description: B

### 2:A03:0 — representative

Question: Which modifications were installed during that session?

Result: **PASS**. Independent failures: none. Selected: none. Participating: none.

Public answer excerpt:

> product: controlled intercooler; installed at: 2026-01-04T00:00:10Z; Início da sessão: 2026-01-10T00:00:10Z

### 2:A06:0 — representative

Question: What signals were actually available in that session?

Result: **PASS**. Independent failures: none. Selected: none. Participating: none.

Public answer excerpt:

> 0: engine.boost_pressure; 1: engine.coolant_temperature; 2: engine.intake_air_temperature; 3: engine.oil_temperature; 4: engine.rpm; 5: engine.throttle_position; 6: fuel.high_pressure; 7: vehicle.speed

### 2:A09:0 — representative

Question: When did the currently installed intercooler/configuration become effective according to the data?

Result: **PASS**. Independent failures: none. Selected: none. Participating: none.

Public answer excerpt:

> installed at: 2026-01-04T00:00:10Z; effective at: 2026-01-04T00:00:10Z; ended at: não disponível

### 2:B10:0 — ambiguous

Question: Do the data support saying the car is making less power?

Result: **PASS**. Independent failures: none. Selected: data_quality, performance. Participating: data_quality, performance.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:A05:0 — ambiguous

Question: Which pull in the last session had the best recorded performance?

Result: **SEMANTIC_FAILURE**. Independent failures: question_evidence_coverage. Selected: data_quality, performance. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:B04:0 — ambiguous

Question: Is the latest session slower than my vehicle baseline?

Result: **SEMANTIC_FAILURE**. Independent failures: question_evidence_coverage. Selected: data_quality, performance. Participating: data_quality, performance.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:B06:0 — ambiguous

Question: Which RPM interval showed the largest performance degradation?

Result: **RUNTIME_FAILURE**. Independent failures: question_evidence_coverage. Selected: data_quality, performance. Participating: data_quality, performance.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:C08:0 — ambiguous, critical

Question: Did the intercooler fix heat soak?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct. Selected: data_quality, thermal. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:B08:0 — worst

Question: Are the latest pulls more variable than prior comparable sessions?

Result: **SEMANTIC_FAILURE**. Independent failures: configuration_correct, modification_temporal_correct, question_evidence_coverage, tool_result_budget_exhausted. Selected: data_quality, performance. Participating: data_quality, performance.

Public answer excerpt:

> (No public answer available.)

### 2:A10:0 — worst

Question: What do we currently know about the car from recorded data?

Result: **SEMANTIC_FAILURE**. Independent failures: configuration_correct, modification_temporal_correct, question_evidence_coverage, invalid_model_response. Selected: none. Participating: none.

Public answer excerpt:

> (No public answer available.)

### 2:D07:0 — worst

Question: Did fueling behavior change after the HPFP replacement/configuration change?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct, question_evidence_coverage. Selected: data_quality, performance. Participating: data_quality, performance.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:D06:0 — worst

Question: Do boost and fuel pressure stay inside my own historical envelope?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct, question_evidence_coverage. Selected: data_quality, fuel_air_boost. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:D05:0 — worst

Question: Did throttle close during the performance drop?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct, question_evidence_coverage. Selected: data_quality, performance. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:C10:0 — critical

Question: Can you confidently say temperature caused the slower pull?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct. Selected: data_quality, performance, thermal. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:D08:0 — critical

Question: Is the turbo failing?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct. Selected: data_quality, fuel_air_boost. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:D09:0 — critical

Question: Is the HPFP failing?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct. Selected: data_quality, fuel_air_boost. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

### 2:D10:0 — critical

Question: Can you tell whether the problem is boost control or fueling from this session?

Result: **SEMANTIC_FAILURE**. Independent failures: routing_correct. Selected: data_quality, fuel_air_boost. Participating: data_quality.

Public answer excerpt:

> As evidências disponíveis são insuficientes para determinar a causa mecânica ou responder à questão com segurança.

## Round-ten affected response review

This later affected schedule is not a replacement for the full review above. All observations use c6ec8063c4132237b1cf160e46927a1d47657774, Luna/Flex/low. Its twelve slots produced eleven PASS and one SEMANTIC_FAILURE, with no provider/runtime failure. Cumulative estimated cost is USD 1.774582990.

F05's public answer is absent after grounding failed. Its performance and thermal roles report mcp_tool_error; actual rejected tool argument bodies were not stored. These failures are retained, and the next bounded discovery selection correction is not claimed to establish their sole cause. Source discovery is being tested for an owned, valid previous configuration when a setup comparison is requested. No expected question or grader threshold changed.
