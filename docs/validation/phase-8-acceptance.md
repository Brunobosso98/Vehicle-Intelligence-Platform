# Phase 8 acceptance — final validation record

Phase 8 implementation acceptance passed on corrected code commit `550844619a5b4e4fc215742e3dd22c0362e3d1d9`. The exact final branch SHA and required workflow receipts for the current report revision are recorded on the existing [PR #40](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/40). The PR remains unmerged.

- Branch: `codex/phase-8-technical-rag-knowledge-intelligence`
- Phase 7D merge/base SHA: `c38c10d3d80c33c3d6699626fc40a620d4b615b4`
- Phase 8 specification commit: `421d422bc3959666dde9f4034995caeca7205896`
- New-PC handoff SHA: `2f6d5c076460648147b0134d551761c4fb873bd0`
- Corrected implementation acceptance SHA: `550844619a5b4e4fc215742e3dd22c0362e3d1d9`
- PR: [#40 — feat: add Phase 8 technical RAG and knowledge intelligence](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/40), OPEN, DRAFT, unmerged.

## Corpus and evidence boundaries

The controlled corpus has 10 reviewed sources (five Tier 1 authoritative, five Tier 2 strong technical), 12 document selections and 23 chunks. Accepted material includes public BMW F30/N55 information, BMW service information available through NHTSA, Bosch fuel/ECU/high-pressure-pump references, Garrett wastegate principles, and official MHD and bootmod3 documentation. The unavailable BMW ST916 source and items without adequate provenance or safe redistribution rights were excluded. Raw copyrighted files and local embeddings are not committed.

Coverage includes N55 architecture, fuel/high-pressure fuel behavior, ECU, boost/wastegate and thermal principles, diagnostics, and tuner documentation/logging. Hardware identity, fuel, exact tuner, map/version, exact tuned targets and some part applicability remain UNKNOWN/PARTIAL when project evidence does not establish them. Stage 2 is not a universal calibration. Stock references do not become tune-specific targets. HPFP interpretation uses recorded commanded/actual values, RPM/load/boost/fuel/configuration/conditions and historical context; no single universal pressure threshold or unsupported failure diagnosis is emitted.

MCP supplies actual vehicle evidence. RAG supplies cited technical documentation. A hybrid conclusion keeps both provenance types and does not let documentary knowledge override telemetry. Missing vehicle data and missing documentation are distinct gaps. Community material is excluded from normative claims. No ECU write, flash, brake, steering or throttle control is exposed.

## Embedding and retrieval results

- Backend: PostgreSQL with pgvector 0.8.2 on the pinned PostgreSQL 17 / TimescaleDB image; cosine vector search and bounded PostgreSQL full-text retrieval.
- Model: `text-embedding-3-small`, 1536 dimensions. Official price verified 2026-10-17 at USD 0.02 per million input tokens: [OpenAI model page](https://developers.openai.com/api/docs/models/text-embedding-3-small).
- Configured spend ceiling: USD 2.00. Recorded real usage: five provider calls, 2,701 input tokens, estimated USD 0.00005402, zero pending reservations. Resume and metadata refresh reused cached vectors; exact-head CI used deterministic/synthetic data and made zero paid calls.
- The 60-case **real-vector** retrieval evaluation passed: Recall@1 0.81173, Recall@3 0.96605, Recall@5 0.99074, MRR 0.96914, precision@5 0.44074. Applicability, trust, citation and knowledge-gap correctness were 1.0; wrong-platform rate and measured fabricated-source, fabricated-citation, wrong-engine normative-use and trust violations were zero.
- Retrieval uses lexical and vector candidates, deterministic reciprocal-rank fusion, then trust, applicability, identifiers, quality and conflict handling. `KnowledgeEvidence` carries source/document/version/chunk/scope/citation and retrieval provenance.
- No retrieval implementation, source manifest or golden case changed after the real-vector checkpoint. The final canonical run did not re-purchase embeddings; the real-vector results remain separately identified from the synthetic CI gates.

## Hybrid acceptance and regressions

Four deterministic disposable DB/MCP/API cases passed: knowledge-only retrieval; HPFP operating context and historical baseline with an unknown exact-map target; an intercooler comparison reporting a -10 K IAT association without claiming causality; and Stage 2 boost with an explicit unknown tune target. Knowledge-only questions do not acquire vehicle summaries. Phase 7B passed 61/61 server scenarios and its corrected browser review keeps a typed same-vehicle documentation gap INCONCLUSIVE with no logging recipe; a cross-vehicle gap stays hidden. Phase 7C passed 23 scored executions, 196 MCP calls, 124/124 valid references and 612/612 supported factual claims.

The final canonical run on the corrected implementation passed the Phase 0–7D deterministic regressions and Phase 8 database, MCP/RAG, browser, benchmark and observability acceptance. The earlier run on `3d9dbd7` had one Phase 7B browser failure: the valid same-vehicle typed documentation gap had no vehicle finding, so the review panel was hidden. Commit `5508446` fixed the scoped UI eligibility and added a cross-vehicle negative test. The corrected full canonical run passed.

The Phase 7D paid-suite caveat remains: all 120 scheduled slots have PASS observations across multiple rounds, but the unified paid 120-case Luna run was not repeated because the API balance was insufficient. The deterministic Phase 7D harness passed. No result here claims that the unified paid run occurred.

## Security, observability and performance

Fresh Trivy 0.75.0 review on 2026-10-17 found zero High/Critical findings in Tempo 3.0.4. Grafana 12.4.13 has five High findings, Collector 0.162.0 four and Prometheus 3.15.0 eight; each accepted residual is scoped by image digest, CVE and package, reviewed on 2026-10-17 and expires 2026-10-23 with a vendor remediation condition. No Critical finding is accepted or suppressed. Exact-head Security, CodeQL Python/JavaScript and dependency review checks passed.

Knowledge ingestion, failure, chunking, embedding spend/cache and retrieval metrics reach Prometheus. Agent retrieval/fusion/evidence/synthesis and operator ingestion/embedding spans reach Tempo. Redaction and credential-leak checks passed.

The canonical benchmark used 100 synthetic SQL samples over seven fixture documents. Hybrid latency was p50 0.007022 s, p95 0.007895 s and p99 0.009752 s. This measures the synthetic database retrieval path; real embedding endpoint latency is reported separately in the local real-provider receipts.

## Exact-head validation and limitations

On corrected implementation SHA `550844619a5b4e4fc215742e3dd22c0362e3d1d9`, exact GitHub checks passed: CI `39063779430`, Security `39063779432`, and canonical full validation `39063779434`. CI reported 1,045 API tests, 95.04% API line coverage and 90.10% branch coverage; the web gate reported 52 tests, 94.74% line coverage and 85.24% branch coverage. Canonical full validation used fresh disposable infrastructure and passed all required stages. The current final branch SHA and its exact required check receipts are linked from PR #40.

Known corpus gaps are the unavailable BMW ST916 material, proprietary tuner/map targets, exact installed parts, and undocumented vehicle configuration. Diagram interpretation, unrestricted runtime web retrieval, forum/community ingestion as normative evidence, and automatic reproduction of the paid Phase 7D suite remain outside scope. These gaps are surfaced rather than filled with model guesses.

See the [traceability ledger](phase-8-traceability-ledger.md) for all 124 specification requirements. PR #40 must remain unmerged for the operator to merge manually.
