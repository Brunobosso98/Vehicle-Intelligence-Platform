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
