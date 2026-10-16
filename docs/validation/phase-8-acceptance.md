# Phase 8 acceptance — in progress

Status: NOT VERIFIED. Working branch: `codex/phase-8-technical-rag-knowledge-intelligence`.
Baseline/specification commit: `421d422bc3959666dde9f4034995caeca7205896`.
Phase 7D merge ancestor: `c38c10d3d80c33c3d6699626fc40a620d4b615b4`.

The original Desktop checkout was synchronized to this branch after the operator explicitly
authorized discarding its prior local changes. Implementation continues in the Desktop repository.
No force-push, remote history rewrite or PR merge has occurred.

## Executed checks (uncommitted implementation checkpoint)

- Focused knowledge cohort: 99 tests PASS (`/tmp/vip-phase8-knowledge-current.log`).
  Four additional paid-CLI preflight cases subsequently passed with the complete 72-case core
  knowledge file (`/tmp/vip-phase8-preflight-unit.log`). Invalid/empty/unapproved provenance is
  rejected before creating a spend ledger or embedding client.
- Current complete API gate PASS: 988 tests, Ruff/format/mypy (116 files), combined coverage
  93.96%, line 95.10%, branch 90.01% (`/tmp/vip-phase8-check-api-frozen.log`). A prior run
  passed 983 tests but failed its branch threshold at 88.81%; source changed during that run.
  The successful repeat used stable API source. No threshold or coverage exclusion was changed.
- TimescaleDB image build PASS: pgvector 0.8.2 / TimescaleDB 2.30.2 / PostgreSQL 17.
- Three real-database integration tests PASS: migration downgrade/upgrade/idempotency preserving
  vehicle counts and telemetry hypertable, atomic publication preserving the old index when
  staging lacks vectors, and immutable source conflicts invalidating cached eligibility. A reviewed
  exact-tune numeric claim renders its operating conditions before the conflict; both conflicting
  sources remain inspectable but produce no claims afterward (`/tmp/vip-phase8-numeric-integration.log`).
- Independent disposable database evaluator PASS: persistence/idempotency, FTS, stored synthetic
  vectors, hybrid fusion, wrong-engine rejection, trust poisoning, document injection, stock/tuned
  gaps, retrieval audit and four actual deterministic MCP/API hybrid/knowledge runs. HPFP operating
  condition assertions and broader hybrid scenarios still need strengthening.
- Reviewed local corpus: eight sources, ten document selections, twenty chunks. No full source text is
  committed. ST916 official PDF acquisition failed; documented gaps remain.
- 60 authored retrieval cases: strict synthetic-vector evaluator PASS, ranking v3,
  Recall@1 0.78395, Recall@3 0.93827, Recall@5 0.97222, MRR 0.94444, precision@5 0.41852;
  knowledge-gap accuracy, applicability, trust and citation checks 1.0; wrong-platform rate 0.
  All five tracked provenance/normative violations were zero. Source/document/chunk snapshots,
  page/section/headings and reviewed numeric facts are compared with the reviewed corpus.
  Receipt: `.validation/knowledge/retrieval-synthetic-v3.json`, log:
  `/tmp/vip-phase8-golden-v3-strict.log`. These **free synthetic-projection metrics do not prove
  real OpenAI embedding quality**. Corpus index: `n55-public-selection-v2-9a7a1ad58faf10f9`.
- Current web gate PASS: 50 tests in nine files, statements 93.54%, branches 85.28%, functions
  90.94%, lines 94.70%; lint/typecheck PASS (`/tmp/vip-phase8-web-a11y.log`). Duplicate knowledge
  landmarks were given distinct accessible names. Production build PASS
  (`/tmp/vip-phase8-web-a11y-build.log`); browser/Axe repeat is ongoing.
- Disposable retrieval benchmark and delivered MCP/retrieval observability gates executed with
  synthetic vectors. Four successful real embedding endpoint latencies were measured (below);
  delivered ingestion/embedding instrumentation still needs proof.
- Browser E2E found and fixed mobile overflow and then a citation-test locator error.
  A further gap assertion used the same incorrect evidence block; that selector was corrected,
  and `/tmp/vip-phase8-browser-current-recheck.log` is the ongoing complete rerun.
- Cloud security gate PASS: checksum review, Gitleaks, Python and Node dependency audits, and
  HIGH/CRITICAL filesystem vulnerability/configuration scan (`/tmp/vip-phase8-security-container-recheck.log`).
  Trivy read the same Desktop files through a read-only container mount with `.git` hidden to
  avoid its preliminary Git worktree traversal. Image scanning/full security remains pending.
- Actual-private-key corpus scans PASS before and after real embedding. The latter checked eight
  raw checksums and twelve local artifacts (`/tmp/vip-phase8-post-embedding-secret-scan.log`).
- Graphify AST update completed: 4,599 nodes / 11,861 edges; subsequent refresh/UI changes
  require another final update.
- Controlled source refresh CLI and reconstruction: 23 synthetic tests PASS, including metadata-only
  versioning, private-key/injection rejection, exact reviewed locators and interrupted-write recovery
  (`/tmp/vip-phase8-refresh-unit.log`). Existing real corpus reconstruction is being checked for
  byte stability. A complete refreshed real index/publication remains pending.

## Real embedding and retrieval checkpoint — 2026-10-15

The operator supplied the existing local `.env` secret. Only presence and configuration validity
were emitted; no key value was printed or persisted. The dedicated confirmed command used
`text-embedding-3-small`, 1536 dimensions and the same durable `.knowledge/embedding-ledger.sqlite`.
Official price was rechecked: USD 0.02 per million input tokens. Conservative preflight projection,
including the smoke, was USD 0.00023734 for ten documents, twenty chunks and sixty golden queries.

Actual smoke plus build: four calls, 2,473 input tokens, calculated cumulative spend USD 0.00004946,
zero pending reservations. Successful endpoint durations: 3.2808, 2.0751, 2.1481 and 1.8487 seconds.
Atomic publication completed in disposable `vehicle_test_phase8_real` with migration 0011/vector 0.8.2.
Receipt: `.validation/knowledge/real-embedding.json`; log `/tmp/vip-phase8-real-embedding.log`.
The immediate confirmed resume made **zero new calls**, retained four total requests/2,473 tokens
and the identical spend. Receipt: `.validation/knowledge/real-embedding-resume.json`.

Real retrieval: all sixty cases PASS using `QueryEmbeddingEncoder/cache_only` and PostgreSQL FTS /
pgvector, without further purchases. Recall@1 0.81173, Recall@3 0.96605, Recall@5 0.99074,
MRR 0.96914, precision@5 0.44074; applicability, trust, citation and gap accuracy 1.0; wrong-platform
rate 0. All five tracked fabricated-source/citation and forbidden normative violations were zero.
An initial 0.96667 gap-accuracy result exposed generic-source masking of an explicit query/MCP engine
conflict. The corrected runtime returns a visible conflict/gap without query encoding or retrieval.
The real-case oracles were not weakened. Receipt: `.validation/knowledge/retrieval-golden.json`;
log `/tmp/vip-phase8-golden-real-runtime.log`.

Index: `n55-public-selection-v2-9a7a1ad58faf10f9`.
Corpus file checksum: `494828e7cd8fbbc07f7eaac832b7f927cead157d44583de1f3e24647058139f3`.
These receipts describe **uncommitted source at the baseline HEAD**, not exact-final-SHA acceptance.
Final committed-head validation must reuse the cache and repeat the relevant gates. Full paid
Phase 7D GPT-6 Luna evaluation was not run.

## Frozen API and strengthened hybrid checkpoint — 2026-10-16

`make check-api` passed on the frozen implementation with MCP 2.2.0: Ruff, formatting,
strict mypy (116 source files), 1,031 unit tests, line coverage 95.03% and branch coverage 90.07%.
The earlier failed coverage attempts remain historical; thresholds were not changed. Boundary tests
now cover corrupt vector cache, invalid spend reservations, headless cache/accounting, invalid pull
duration, omitted unitless values and preservation of co-recorded units.

The independent disposable PostgreSQL/MCP/API evaluator passed all four strengthened cases with
zero paid calls. HPFP/boost use actual recorded sample values with Pa/rpm/% units, effective tuned
Stage 2 context, applicable documentary evidence and an explicit unavailable exact-map target.
HPFP also requests its configuration's historical baseline. Intercooler executes the actual Phase 5
comparison, checks the independently constructed -10 K IAT delta and returns ASSOCIATION with an
explicit rejection of mechanical causality. Knowledge-only questions do not acquire vehicle summaries.
These are synthetic vehicle scenarios over real database/MCP/API execution, not actual vehicle tests
or a paid Luna validation. Logs: `vip-phase8-check-api-boundaries-final.log` and
`vip-phase8-hybrid-final-mcp22.log` in the local validation checkpoint.

The no-network ingestion/embedding instrumentation probe delivered every required counter and its
operator/ingestion/embedding spans to Prometheus/Tempo; actual agent traces include intent, retrieval,
combined SQL selection, fusion, evidence and synthesis. A current 100-query synthetic SQL benchmark
measured hybrid p50/p95/p99 0.0790/0.1166/0.1379 seconds on seven authored fixture documents. Real
embedding endpoint latencies are separately recorded in paid-command receipts, avoiding attribution
of synthetic-vector performance to OpenAI. Containers rebuilt successfully with MCP 2.2.0.

## Outstanding mandatory validation

Expanded-corpus checkpoint, October 16: two reviewed supplier sources add three generic
ECU/torque/ignition/wastegate-principle chunks. Ten sources / twelve selections / twenty-three
chunks are indexed. Real usage is now five requests / 2,701 tokens / USD 0.00005402 / zero pending
reservations. `real-expanded-embedding.json` and `real-expanded-golden.json` record one incremental
provider call, reuse of the prior corpus and unchanged passing sixty-query metrics. Reconstruction
format v3 derives its timestamp from reviewed provenance, so identical manifests compiled to
different output paths produce identical immutable index snapshots.

Current unit knowledge gate: 128 tests PASS before the final reconstruction/probe additions;
the focused reconstruction/query repeat then passed 39 tests. Browser gate PASS with fresh
caption, zero scoped Axe issues and no desktop/mobile overflow (`vip-phase8-browser-canonical-path-oct16.log`).
Impeccable finish review: ship for the verification-caption correction; documenter: no changes
needed for the ordinary extension. Baseline side-border/Arial findings remain standing, with
no suppressions. Deterministic Phase 7D harness acceptance passed (`vip-phase8-phase7d-compat-recheck.log`);
its deliberately measured semantic failures remain in the receipt, and it does not validate Luna.

October 16 refresh checkpoint: bootmod3 source verification version 2 corrects EWG applicability
to an explicit hardware requirement, leaving actual vehicle hardware unknown. The original
twenty chunks and all embeddings were reused; complete index
`n55-public-selection-v2-b8d4e43dd9182ea8` published with zero new provider calls. Cumulative usage
remains four requests / 2,473 tokens / USD 0.00004946 / zero pending reservations.
`real-refresh-embedding.json` and `real-refresh-golden.json` under `.validation/knowledge/` record
publication and sixty actual-vector queries: Recall@5 0.9907407, MRR 0.9691358, applicability/trust/
citation/gap correctness 1.0, wrong-platform rate and the five measured violations zero.
Disposable integration checks passed (3 tests), including preservation of both immutable versions
when text is unchanged. Migration `0012` fixes the old text-uniqueness constraint without editing
applied revision `0011`. These receipts still describe uncommitted source, not final-SHA acceptance.
The canonical manifest has been updated; its final reconstruction receipt must also be repeated.

Hybrid operating-condition/history, browser, delivered instrumentation and benchmark checkpoints
above have executed. Their final committed-head repeats, complete security and Phase 0–7D
deterministic regressions, clean-state/exact-final-SHA validation and mandatory GitHub checks remain
pending. Draft PR [#40](https://github.com/Brunobosso98/Vehicle-Intelligence-Platform/pull/40)
is open against main and remains unmerged. The existing real vector cache
and cumulative ledger must be retained; future refreshes share the same absolute USD 2 ceiling.
No final-SHA or VERIFIED claim is made.

## Regression follow-up — 2026-10-16

The first committed implementation (`31fe69a`) did not pass canonical remote acceptance.
Formatting failures were corrected without changing the source-manifest or golden JSON semantics.
Phase 7B/7C regressions exposed documentary answers bypassing the Supervisor artifact and explicit
operator review. Documentary-only answers now retain the existing Supervisor report without vehicle
specialists or telemetry calls. An explicit investigation request can review a typed documentation
gap as INCONCLUSIVE; it cannot create a logging recipe to supply missing documentation.

Local follow-up runs then exposed measurement questions being classified as documentary-only:
“Why did boost fall?” and “Why is fuel pressure missing during a pull?”. These stay on the vehicle
path. New hybrid classification checks also distinguish absent/unreliable vehicle evidence from
missing documentation, preserve documentary provenance and lower confidence for insufficient
vehicle evidence. The corrected frozen source passed `make check-api`: 1,042 tests, strict mypy
(116 source files), Ruff/format, line coverage 95.04% and branch coverage 90.09%. The independent
four-case hybrid evaluator passed again with zero paid calls. Container builds and docs/contracts
checks passed. Logs: `vip-phase8-api-routing-final.log`, `vip-phase8-hybrid-routing-recheck.log`,
`vip-phase8-containers-routing.log` and `vip-phase8-doc-contract-routing.log`. Phase 7B/7C
independent regression runs subsequently advanced to two further failures: a documentary-only run
kept unknown token accounting instead of measured zero, and a question about unknown fuel pressure
still selected the documentary path. Both were corrected, with 106 focused knowledge/orchestration
tests passing (`vip-phase8-gap-routing-unit.log`). New Phase 7B/7C runs and the final full API repeat
remain pending; this remains a development checkpoint rather than final committed-head acceptance.

The next independent Phase 7B repeat passed all 61 scenarios with zero invented signals,
approval bypasses, cross-vehicle leaks, unsupported diagnoses, unsafe calls or budget violations
(`vip-phase8-investigation-gap-recheck.log`). The 1,045-test local API run also passed its assertions;
its coverage artifacts overlapped with a duplicate run, so its local coverage attribution is not
used as final evidence. The duplicate was stopped and an isolated `make verify` repeat started.
GitHub quality passed at `f5fae6a`. Its CodeQL aggregate separately reported a HIGH finding at the
operator download's implicit SSL context. The downloader now explicitly requires TLS 1.2 or newer;
all eleven download-boundary cases pass with certificate and hostname verification retained
(`vip-phase8-tls-security-unit.log`). Updated-head CodeQL verification is still required.

Security remains a failed gate: the committed risk-acceptance policy has seventeen observability
exceptions expiring October 15, 2026. They have not been renewed or suppressed. A disposable scan
of official Tempo 3.1.0 still reports four HIGH/CRITICAL findings, so a major Tempo upgrade alone
would not satisfy the gate. No retained observability volumes have been migrated. Full security
resolution and final exact-head GitHub checks remain required before verification.
