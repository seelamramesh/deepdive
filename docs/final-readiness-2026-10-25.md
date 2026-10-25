# Final offline readiness review — 2026-10-25

Submission remains on hold. No paid Mesh or Brave calls were made during this pass. This is an evidence review, not a guarantee that reports are correct or complete. Historical runs are not rewritten.

## Final fixes

- Brave queries are normalized and locally compacted to at most 600 characters and 75 words before dispatch. Complete tokens and quoted phrases are retained where possible; this is keyword compaction, not semantic query rewriting. Original/submitted queries and lengths are recorded. HTTP 422 remains an error; an uncompactable query is rejected locally without dispatch.
- Numeric report sentences require locally linked claim/evidence citations and the numeric literal/explicit unit in the cited passage. Offending lines are withheld, not given invented citations. Approved-claim fallback receives the same checks and includes all approved passages. This necessary lexical guard cannot establish semantic entailment or validate arithmetic. Non-numeric factual claims still depend on model review and link checks.
- Audit exposes withheld numeric lines and compacted queries. Mobile run-drawer questions wrap fully.
- The copied Action 3 fixture exercises the passage-placement regression. Production records remain historical, so old report unit 7 still shows its original citation gap.

## Measured self-evaluation

| Metric | Action 2 | Action 3 |
|---|---:|---:|
| Run | ee166f04883a48c0 | b23afbee4eda46e0 |
| n8n execution | 414891 | 414929 |
| Logical agent calls | 20 | 25 |
| Physical Mesh requests | 20 | 22 |
| Brave requests | 2 | 2 |
| Local exact-cache reuses | 0 (cache active) | 3 (12%) |
| Prompt / completion tokens | 36,896 / 24,341 | 41,413 / 30,616 |
| Total recorded tokens | 61,237 | 72,029 |
| Webhook latency | 136.110 s | 161.051 s |
| Sources / passages | 1 / 9 | 2 / 12 |
| Accepted / active claims | 1 / 2 | 1 / 2 |
| Coverage | 4 red, 1 yellow | 5 red, 1 yellow |
| Retained contradictions | 0 | 0 |
| Reservations, not billed charges | $0.702245 | $0.543220 |

Different questions, source limits and output caps prevent a controlled cache comparison. Cached-event duration was recorded as zero rather than precisely timed. No billing savings or counterfactual latency reduction is proven. Four-stage failure/timeout and temporal/false-premise tests are mocked; they are not live accuracy measurements.

## All 20 stored runs: weak-area review

- Action 3 round two reused the same complete source windows (5,339 and 4,348 characters, below the 7,000-character window). Two unattempted URLs carried forward, but different-window gap recovery and natural failed-fetch backfill were not demonstrated live. Offline tests cover those paths.
- Source-critic scores .68 and .74 exceeded the current .4 threshold. Two `ineligible_result` events were empty contradiction arrays not cached; one `response_not_stored` was a truncated prosecutor response. These are not useful sources rejected by the critic. No calibration gold set exists; threshold was not tuned.
- Probable journal/preprint duplicate in `eval20261024exo01`: IOP DOI URL `10.3847/2041-8213/adc1c8` and arXiv `2504.12267`. Current title heuristic groups them; different URL counts are not independent study counts. There are no recorded DOI identifiers for that pair.
- Only 10 of 66 source records retain full snapshots. Fourteen of 20 runs lack retrieval audits. Springer `10.1186/s12902-024-01727-w` and PMC `PMC9524196` records in `8f567d3d99df44ff` are retrospectively flagged as possible access/challenge pages from metadata, but have no full snapshots for definitive classification. Do not certify all legacy retrievals clean.
- Four legacy contradiction records exist: one in `8f77bd09f8ce4740`, three in `f8d346b8b04040ac`. They were not independently revalidated. Current guarded Action 2/3 retained zero; positive retention accuracy remains unproven. The claim that no live run ever retained a contradiction is incorrect.

## Geotab negative finding

Run `c324ed4de85d4e3c`, evidence `93d4385dbced`, states 10,000+ EVs, about 1.8% annual degradation and LFP 1.2–1.5%. [Geotab's 2024 primary release](https://www.geotab.com/uk/press-release/2024-battery-degradation/) reports 1.8% on approximately 5,000 EVs. [January 2026 release](https://www.geotab.com/press-release/ev-battery-health-degradation-fast-charging-study/) reports 2.3% across 22,700+ EVs and 21 makes/models. The historical 1.8% is not inherently false, but needs a 2024 qualifier; the quoted cohort/LFP range was not corroborated by these inspected primary releases. The historical run remains unchanged.

## Browser verification

Seven actual views: Report, Coverage, Courtroom, Audit, Contradictions, Sources, Control Flow. Evidence is embedded in Report/Sources; certificate in Audit. Browser checks covered 360, 375, 390 and 412 px, plus desktop 1280 px. A separate request for 412 initially yielded 413; the viewport was corrected and actual innerWidth checked. No page overflow or visible input/button/summary target below 44 px was found in the four-width view sweep. Mobile drawer opens and scrolls; body/run-question text inspected at 16 px. Arrow-key tab switching works; New research opens without dispatching a run. No active run existed, so live cancellation was not exercised. Physical Android and notched safe areas remain untested.

Action 3 Audit shows three reuses (researcher twice, source_critic once), twelve first misses, ten different-key misses, and the Brave 422. Action 2 had cache deployed and zero reuses; it must not be labeled unavailable. Older records lacking cache metadata remain unavailable. Control Flow intentionally separates shared architecture from per-run recorded events.

## Ledger reconciliation

Actual schema is `reservations/kind/reserved_usd`, with `cap_changes`.

| Proven interval | Mesh | Brave | Entries | Reserved USD |
|---|---:|---:|---:|---:|
| Prior mixed evaluation reservations | 63 | 3 | 66 | 2.138282 |
| Action 2 | 20 | 2 | 22 | 0.702245 |
| Action 3 | 22 | 2 | 24 | 0.543220 |
| Total | 105 | 7 | 112 | 3.383747 |

Exact decimal sum matches the ledger. Stop is $3.50, authorization $4, remaining reservation capacity $0.116253. One recorded cap change raised the reservation stop from $2.50 to $3.50 under explicit $4 authorization. Do not rewrite that history as a different ledger event. Prior 66 reservations cannot be attributed to all prior 18 stored runs. Older entries lack idempotency IDs/timestamps; identical amounts alone cannot establish duplicates or prove uniqueness. Action 2/3 physical request logs match their reservation intervals.

Brave billing dashboard required login. Mesh account access was attempted from its official site; billing remains unverified without an authenticated account session. No credentials were copied into browser/source/chat. Reservation is not billed cost. Production has no durable cost ledger or production-wide budget guard; guard is evaluation-only. Missing historical usage is unknown, not zero. A crash can lose in-flight billing metadata; saved checkpoints do not automatically resume execution.

## Official rules and CI

Official authenticated [Agent Arena dashboard](https://career.krishnaik.in/dashboard/hackathons?h=agent-arena-2026) and DeepDive brief were read on October 25. Site displayed registered status, submissions open, deadline October 30, 2026 at 12:30 PM CDT.

| Requirement | Evidence and limitation |
|---|---|
| Python Flask/FastAPI | `app/main.py`, `requirements.txt`: FastAPI |
| All inference through Mesh | `app/core/mesh_gateway.py`, `tests/test_mesh_compliance.py`; cache reuse makes no inference request |
| Three genuinely distinct agents | Twelve distinct prompts in `app/agents/prompts.py`, dispatch in `runner.py`; coordinator is ordinary Python |
| Real ingestion and provenance | `retrieval.py`, schemas, SQLite; snapshot gaps in old records disclosed above |
| Claim verification and rejection | Prosecutor/defense/judge, report verifier and deterministic citation checks; partial support and uncovered areas remain |
| Research loop | Orchestrator coverage/gap transitions; two rounds observed |
| Auditable decisions | Per-run search, state, calls, verdicts, coverage and internal certificate |
| Reproducible self-evaluation | Tests, Action 2/3 records and measured table; no invented benchmark score |
| Public code, README, dependencies | Public repository, setup/design/evaluation documentation |
| Secrets excluded | `.gitignore`, `.env.example`; official advisory passed; no values disclosed |
| Optional vector DB | Not implemented; SQLite is not vector search; suggested stack, not mandatory rule |
| Optional video and deployment | Live deployment exists; no completed demo video claimed |
| Solo/team eligibility | Account shows registered; personal eligibility/team declarations remain user responsibility |

Exact historical `2c0f5ad6228b431fbfee46d4138b5a7eb2f58629`: backend and frontend CI succeeded ([app CI](https://github.com/seelamramesh/deepdive/actions/runs/40165642301)). Organizer [job](https://github.com/seelamramesh/deepdive/actions/runs/40165639923) passed 4/4 critical checks plus advisories, then failed reporting with HTTP 403 because no submission entry exists. The job is failed and the result is not recorded; this is not fully green CI. It is not resolved by changing the official workflow or prematurely submitting. Latest-revision CI/release proof is recorded separately after push.

## Feature inventory and negative results

| Capability | Evidence | Boundary |
|---|---|---|
| Twelve Mesh roles | Source, observed guarded runs | Do not claim all twenty legacy runs used all current roles |
| Claim courtroom / report verification | Live rejection plus copied-fixture numeric regression | Necessary checks, not proof of truth |
| Contradictions | Current comparison trace, mocked cases, four legacy records | No independently measured positive accuracy |
| Exact cache | Three of 25 logical calls reused | Run-only, 128 entries, five-minute TTL; no semantic cache |
| Backfill / window selection | Offline tests; carryover observed | Failure recovery not naturally triggered in guarded live run |
| Qualifier feedback | Four attributed round-two critiques observed | CTrip call-center/volunteer/nine-month qualifier closure incomplete |
| Artifact limitations | Ten generated units including heading in Action 3 | Counts are internal; report still incomplete |
| Observability | HTTP 200/422 trace and cache miss reasons | Legacy missing measurements stay unknown |
| Budget guard | Durable guarded evaluation entry point | Not normal production entry point |
| n8n | Fourteen-node polling workflow; executions above | Does not call agents directly; polling adds delay |
| Mobile UI | Browser viewport/keyboard checks | No physical Android/notch test |

Remaining negative results: five red/one yellow coverage after two rounds; one accepted claim in each guarded run; zero retained contradictions in those runs; over-limit Brave query found; passage-placement defect found; incomplete qualifiers; unknown actual billing; untimed cache-event zero durations; no independent cached/uncached control run; historical probable duplicates and incomplete retrieval snapshots. New guards were tested offline, not validated by another paid research run.

Final decision: code can be presented with these disclosures, but research completeness is not demonstrated. Keep submission and merge on hold for the user's explicit decision. Do not call every feature/scenario fully validated.
