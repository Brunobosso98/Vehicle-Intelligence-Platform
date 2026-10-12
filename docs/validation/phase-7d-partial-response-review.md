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
