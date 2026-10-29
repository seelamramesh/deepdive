# Action 3 evaluation results — 2026-10-25 America/Chicago

## Outcome

One guarded paid n8n run and two offline test groups completed. **Execution and measurement passed; research completeness remains insufficient. No hackathon submission made.**

[Live run b23afbee4eda46e0](https://deepdive.example.invalid/run/b23afbee4eda46e0) · [Machine-readable measurements](evaluations/action3-n8n-2026-10-25.json)

Topic: compare productivity findings from the Chinese CTrip call-center and Indian data-entry randomized studies, preserving population/work-arrangement qualifiers and distinguishing genuine contradictions from contextual differences. Primary source pages: [NBER w18871](https://www.nber.org/papers/w18871) and [NBER w31515](https://www.nber.org/papers/w31515). Different populations/tasks mean opposite effect directions do not automatically establish a like-for-like contradiction.

Runtime `26907d9` remained the deployed backend. Temporary evaluation wrapper and offline test source: `6464cee`. No core production code was changed during this evaluation.

## Protocol and limits

- Exactly one production n8n webhook dispatch; no retry or second topic.
- Maximum two rounds, two retained sources across the whole run, two active claims, one search query per round, four fetch attempts per round and one contradiction batch per round.
- Output cap 2048 and up to two JSON attempts. Action 2 used a 4096 output cap. Source cap and output cap affect interpretation of quality, token use and reservations.
- Shared exclusive process lock, durable one-shot admission marker and before-request reservations were installed on the production n8n path. Normal service was temporarily replaced with the same backend image plus a tested guard entry point, then restored.
- The $0.62 planning allowance was recorded in the pre-run sidecar plan, not double-counted as an upfront reservation. Hard new reservation ceiling $0.65; cumulative stop $3.50. The planning calculation repriced Action 2's requests at 2048 maximum output tokens and added an allowance for the second source and comparison work. No cache savings were assumed; completion was not guaranteed.
- Two primary pages were checked with ordinary HTTP before launch. Official Mesh pricing metadata was also read; neither was a Mesh inference or Brave search request. No unguarded paid research request was sent.

## Execution, usage and latency

| Metric | Measured result |
|---|---:|
| Backend status / rounds | END / 2 |
| n8n execution | 414929, success |
| Webhook status | HTTP 200, complete |
| Webhook wall time | 161.051 s |
| n8n saved execution duration | 161.005 s |
| Backend to last checkpoint | 160.876874 s |
| Logical recorded agent attempts | 25 |
| Actual Mesh dispatch attempts / response events | 22 / 22 |
| Brave dispatch attempts | 2 |
| Prompt tokens | 41,413 |
| Completion tokens | 30,616 |
| Total tokens | 72,029 |
| Sent attempts missing token fields | 0 |
| Summed recorded Mesh durations | 158.769 s |
| Mean sent-attempt duration | 7.216773 s |
| Transient failed completion attempts | 1 prosecutor response truncated at output limit; compact retry succeeded |
| Final run warnings / error | None / null |

Webhook report and certificate exactly match workspace artifacts. Saved n8n records confirm the run ID, Get Report, Get Certificate and Respond Success. Wait ran 32 times, with recorded durations 5000–5003 ms. The single repaired completion failure is included in usage/reservations, not hidden by the final END state.

## Five fix observations

| Fix | Result | Evidence and limit |
|---|---|---|
| Retrieval backfill | **NOT TRIGGERED naturally; carryover observed** | Both primary seeds returned 200, so no seed-failure replacement was needed. Two unattempted round-one URLs carried into round two. Extra fetches were explicitly blocked by the evaluation-only two-source cap, not reported as HTTP failures. Offline tests cover failure backfill and no-repeat behavior; this run does not prove live failure recovery. |
| Search/retrieval observability | **OBSERVED** | Search outcomes were 200/success then 422/error. Actual page retrievals recorded 200 with safe IDs, timestamps and durations. Evaluation-cap skips have no HTTP request/status and are separately labeled. |
| Qualifier feedback | **OBSERVED, partial semantic outcome** | First drafter input had no prior feedback; second contained four attributed judge/prosecutor critiques. First-round claims were both partially supported. The revised Indian claim added scope evidence and became supported; the CTrip claim still omitted qualifiers and stayed partially supported. No independent causal A/B test. |
| Deterministic limitations | **OBSERVED** | Final report contains ten separate deterministic artifact units in addition to five retained model-derived units. Model reviewer approved 16 of 17 generated units; only five remained after citation filtering. Five units do not mean five verified claims. |
| Cache telemetry | **OBSERVED** | All 22 misses have recorded reasons; three reuses reference original calls, match agent/model/prompt/input/output metadata and add zero tokens. |

## Cache

| Metric | Actual observation |
|---|---:|
| Local reuses | 3 / 25 logical calls = 12% |
| Reused agents | researcher twice, source critic once |
| Miss reasons | first: 12; different_key: 10 |
| Storage outcomes | stored: 19; ineligible_result: 2; response_not_stored: 1; reused: 3 |
| Provider cached-prompt tokens | 0 across 22 provider responses |
| Cache-origin metadata matches | 3 / 3 |
| Incremental tokens on reuse | 0 |
| Independent cached/uncached live control run | None |

The snapshots were short enough to reuse in full across both rounds, rather than selecting a different window. Original-call hashes and source-call IDs match on each reuse. Cache event duration is recorded as zero by the current branch; it is not a precise separately timed latency saving. No counterfactual saved-token total or provider discount is claimed. An unchanged cached response does not independently prove research correctness.

## Quality and comparison

| Metric | Action 2 | Action 3 |
|---|---:|---:|
| Retained source pages | 1 | 2 |
| Primary research/regulatory pages | 1 | 2 |
| Evidence passages | 9 | 12 |
| Final active claims | 2 | 2 |
| Accepted claims | 1 | 1 |
| Final partially supported claims | 1 | 1 |
| Retained contradictions | 0 | 0 |
| Coverage | 4 red, 1 yellow | 5 red, 1 yellow |
| Areas with zero evidence | 1 / 5 | 3 / 6 |
| Final model-derived units, including headings | 5 | 5 |
| Deterministic units, including heading | 0 | 10 |
| Cache reuse | 0 / 20 (0%) | 3 / 25 (12%) |
| Mesh sent attempts | 20 | 22 |
| Total tokens | 61,237 | 72,029 |
| Webhook wall time | 136.110 s | 161.051 s |
| New request reservations | $0.702245 | $0.543220 |
| Confirmed billed charges | Unknown | Unknown |

Topics, source coverage, number of subquestions, total-source cap and output limit differ. This is a descriptive comparison, not evidence that the fixes caused a speed, cost or accuracy improvement. Source-critic flags and scores remain model assessments; they are not independent certification.

Within Action 3, accepted claims rose from zero after round one to one after round two. The Indian result gained linked population/design evidence; CTrip remained partially supported. Most comparison questions are still unanswered. No claim of complete gap recovery is made.

The contradiction detector compared one cross-source pair in each round and returned no candidates. It was not skipped, but a positive real-world contradiction-retention case is still unproven. Different contexts and only one finally accepted study result prevent treating this as consensus or validated contradiction recall.

## New findings retained

1. **Search query policy violation.** Round-two query had 543 characters and 82 whitespace-separated words. Current [Brave web-search reference](https://api-dashboard.search.brave.com/api-reference/web/search/get) allows 600 characters and 75 words. The request returned 422. The over-word-limit query is an observed policy violation; the exact response-body validation reason was not logged. Add local query validation/compaction before another paid search, without silently treating errors as empty results. No paid retry was made.
2. **Qualifier closure is incomplete.** Feedback transport works, but the CTrip claim still omitted call-center volunteer and duration scope. Do not lower verification thresholds or declare the claim corrected. Some prosecutor/judge critiques also interpret 'We first find' as preliminary status; that interpretation is not independently established and should not become evidence by repetition.
3. **Clause-to-passage citation placement gap.** Report unit 7 cites `f218324b19a3` for random allocation, then states the 18% result with only a claim marker. That cited excerpt does not contain the number; `6da09bb0c613` does. The same primary source supports the result and the executive summary cites it correctly, so this is a passage-level traceability gap, not an invented statistic. Paragraph-level marker checks and model review did not fully enforce sentence-level support. Preserve this negative result for the next offline review.
4. **Completeness remains low.** Five red areas, three without evidence, and one accepted claim cannot answer the requested two-study comparison. Deterministic limitations accurately expose the gaps; adding those units is not additional substantive research.

## Offline Test A — unsupported temporal premise

**PASS for the mocked contract.** Question: “What caused the 2025 Mars crewed landing failure?” The mocked researcher returned a plausible fabricated event passage absent from supplied source text. Real extraction rejected it; the drafter did not receive fabricated evidence. The run ended with explicit insufficient verified evidence and no fictional finding. This does not establish live model temporal judgment or verification of a real-world spaceflight timeline.

## Offline Test B — four failure cases

| Case | Result | Actual contract checked |
|---|---|---|
| Drafter timeout before any accepted claim | PASS | FAILED with sources/evidence persisted, explicit error and no invented verified report/certificate. An early fatal error is not falsely promoted to a verified partial report. |
| All retrievals fail | PASS | END with explicit insufficient-evidence report and no accepted claims. |
| Caught failure after accepted checkpoint | PASS | Accepted work survives with a labeled checkpoint warning and report. This is an injected timeout, not a hard process-kill or automatic-resume test. |
| Search URLs yield error pages | PASS | Mock HTTP 404 is classified as failed retrieval with status/error fields; no error page becomes evidence. |

All HTTP/Mesh I/O mocked; real HTTP transports blocked by shared pytest fixture. Full local backend: 199 passed, one Linux-only lock skip. Isolated deployed Linux image with guard/test overlays: 21 guard/offline tests passed, including lock contention. [Backend/frontend CI for wrapper source passed](https://github.com/seelamramesh/deepdive/actions/runs/40164926476). These mocked results are not live accuracy measurements.

## Reservation accounting and restoration

| Item | Recorded amount |
|---|---:|
| Before Action 3 | $2.840527 |
| Planning allowance | $0.62; not a charge or duplicate upfront reservation |
| Hard new-reservation ceiling | $0.65 |
| Added reservations | $0.543220 |
| Cumulative reservations | $3.383747 |
| Conservative stop | $3.50 |
| Remaining reservation capacity | $0.116253 |
| Authorized total | $4.00 |
| Confirmed billed | Unknown |

Added entries: 22 Mesh and two Brave reservations. Every dispatch was preceded by a matching durable reservation; all 88 prior entries and authorization history were preserved. No refunds, ledger reset or cap increase. Actual provider charges cannot be inferred from conservative reservations.

Normal uvicorn entry point restored on runtime `26907d9`, guard mount absent, process lock released. Independent public readiness and SQLite integrity checks passed; 20 runs now saved, no active runs. Every one of the 19 prior stored JSON records exactly matches pre-run backup. The completed run is visible in UI; Audit shows three local reuses, miss reasons, HTTP 422 and deterministic limitations. No physical Android check was added.

## Next gate

Action 3 execution and measurement are complete; the overall goal is not complete and submission remains on hold. Actions 4–8 await confirmation. Their review/browser/documentation work needs no new Mesh/Brave inference/search, but actual billing reconciliation still requires provider charge evidence. Prioritize local query-policy regression and citation-placement review, then reassess completeness. Do not start a second paid run or assume $0.116253 can fund a full evaluation.

## Per-call appendix

| # | Agent | Event | Miss reason | Prompt tokens | Completion tokens | Recorded ms |
|---:|---|---|---|---:|---:|---:|
| 1 | planner | sent | first | 260 | 1947 | 11150 |
| 2 | search_strategist | sent | first | 1533 | 1155 | 6294 |
| 3 | researcher | sent | first | 3130 | 1176 | 4470 |
| 4 | researcher | sent | different_key | 2626 | 1223 | 6656 |
| 5 | source_critic | sent | first | 5582 | 1868 | 9816 |
| 6 | claim_drafter | sent | first | 2108 | 833 | 5302 |
| 7 | prosecutor | sent | first | 645 | 1804 | 10285 |
| 8 | defense | sent | first | 568 | 921 | 4695 |
| 9 | judge | sent | first | 1923 | 1625 | 8186 |
| 10 | contradiction_analyst | sent | first | 999 | 521 | 4324 |
| 11 | coverage_analyst | sent | first | 2220 | 2048 | 8063 |
| 12 | search_strategist | sent | different_key | 3299 | 844 | 5079 |
| 13 | researcher | reuse | - | 0 | 0 | 0 |
| 14 | researcher | reuse | - | 0 | 0 | 0 |
| 15 | source_critic | reuse | - | 0 | 0 | 0 |
| 16 | claim_drafter | sent | different_key | 3447 | 1464 | 8190 |
| 17 | prosecutor | sent | different_key | 866 | 2048 | 10993 |
| 18 | prosecutor | sent | different_key | 944 | 1511 | 9041 |
| 19 | defense | sent | different_key | 789 | 1206 | 5384 |
| 20 | judge | sent | different_key | 2451 | 1726 | 7583 |
| 21 | contradiction_analyst | sent | different_key | 1220 | 475 | 4375 |
| 22 | coverage_analyst | sent | different_key | 2332 | 2048 | 8276 |
| 23 | synthesizer | sent | first | 2036 | 1801 | 9912 |
| 24 | report_verifier | sent | first | 1541 | 1748 | 7458 |
| 25 | report_verifier | sent | different_key | 894 | 624 | 3237 |
