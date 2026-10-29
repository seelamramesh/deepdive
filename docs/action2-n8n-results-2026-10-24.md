# Action 2 measured results — 2026-10-24 America/Chicago

## Result

One authorized n8n evaluation completed. **Technical execution passed; answer completeness is insufficient. No positive cache savings demonstrated.** No Action 3 run or hackathon submission was launched.

[Saved run](https://deepdive.example.invalid/run/ee166f04883a48c0) · [Machine-readable measurements](evaluations/action2-n8n-2026-10-24.json)

Topic: FDA/USDA federal oversight of cell-cultivated chicken and the limits of FDA pre-market consultation.

Runtime: `30312f9`; temporary evaluation wrapper source: `a88f80b`. Explicit user confirmation received after the earlier launch rejection. The controller launched once, passed admission/lock/reservation pre-flight, and restored the original production container entry point afterward. Workflow was not edited.

## Execution and latency

| Metric | Actual observation |
|---|---:|
| Run | `ee166f04883a48c0`, END |
| n8n execution | 414891, success |
| Workflow | `vXuzyMGtoaIr2Gcu`, version `9e0edda7-3082-4f5a-97d5-e7265edde36e` |
| Webhook | HTTP 200, `status=complete` |
| Webhook wall time | 136.110 s |
| n8n saved execution duration | 136.044 s |
| Backend to final checkpoint | 131.564844 s |
| Summed recorded Mesh durations | 128.906 s |
| Mean uncached Mesh duration | 6.4453 s |
| Mean cached duration | Not applicable: no hits |
| Rounds | 2 |
| Wait node visits | 27, recorded 4999–5001 ms each |

Get Report, Get Certificate and Respond Success executed. Webhook report and certificate exactly match saved workspace artifacts. The n8n connector returned an internal error for execution details; read-only n8n SQLite records independently confirmed the execution and run ID. No webhook retry was attempted.

## Cache, tokens and search

| Metric | Actual observation |
|---|---:|
| Recorded agent calls | 20 |
| Local exact-cache hits | 0 |
| Local hit rate | 0/20 = 0% |
| Mesh dispatch attempts / responses | 20 / 20 |
| Prompt tokens | 36,896 |
| Completion tokens | 24,341 |
| Total tokens | 61,237 |
| Calls missing any token field | 0 |
| Provider cached-prompt tokens | 0 across all 20 responses |
| Brave reserved dispatch attempts | 2 |
| Searches returning URLs | 1 of 2 |
| Transport errors / malformed completion attempts | 0 / 0 |
| TTL-expired entry count | Not instrumented; unknown |
| Different-key miss count | Not instrumented; unknown |

There is no cached-response quality sample and no second uncached control run. No counterfactual saved tokens, saved latency, or provider billing discount is inferred. The same FDA snapshot was analyzed at offsets 0–7000 in round 1 and 3500–10500 in round 2. This demonstrates a different window selection, not successful gap closure. Repeated agent names alone do not create an exact-key match. Missing cache-reason telemetry prevents attributing every miss to a specific cause.

## Quality

| Metric | Actual observation |
|---|---:|
| Retained sources | 1 |
| Primary sources | 1 FDA page; official domain, also model-classified primary |
| Evidence passages | 9 |
| Final active claims | 2 |
| Accepted claims | 1 |
| Partially supported / fully unsupported active claims | 1 / 0 |
| Contradictions retained | 0 |
| Subquestions with zero evidence | 1 of 5, applied cases |
| Subquestions with no accepted claim | 4 of 5 |
| Model report review | 19 units approved, 0 withheld |
| Units included after citation filtering | 5 |
| Approved units absent from final report | 14 |
| Warnings / run error | None / null |

Claim counts above describe the final active budget, not all generated candidates. Selection history includes a merged duplicate and an earlier partially supported claim excluded from the two-claim active budget. The final non-accepted claim is partially supported; calling it fully false would misstate the judgment.

Coverage scores are recorded model assessments, not calibrated accuracy percentages. Counts are derived from saved artifacts.

| Area | Score | Status | Passages | Accepted claims |
|---|---:|---|---:|---:|
| Agency boundaries | 0.20 | red | 3 | 0 |
| Consultation process/legal effect | 0.35 | yellow | 4 | 1 |
| Determinations established | 0.10 | red | 1 | 0 |
| Residual obligations | 0.10 | red | 1 | 0 |
| Applied cases | 0.00 | red | 0 | 0 |

The one accepted factual point concerns voluntary consultation. The report explicitly says it cannot answer the division of agency oversight or consultation scope. With one source and unresolved coverage, zero contradictions cannot establish agreement or contradiction-detection recall. Certificate citation coverage of 1.0 is an internal linkage metric, not a claim that the question was answered.

## Findings to address before broader evaluations

1. **Retrieval does not fill failed-source slots.** The FDA seed was retained. The USDA-FSIS seed failed with `HTTPStatusError` in both rounds; the trace does not record an HTTP status code. Round 1 Brave supplied two additional URLs, but the two-source selection budget selected only the seeds. After USDA retrieval failed, those alternatives were not fetched. Round 2 did not carry those earlier alternatives forward.
2. **Search failure observability is incomplete.** Round 2 returned no URLs or search was unavailable; current trace cannot distinguish an empty result from a swallowed HTTP error. Preserve status/error classes without secrets and create short, targeted queries before another paid run. Do not infer a particular HTTP error from this evidence.
3. **Scope repair did not close the gap.** Judge identified missing species/stage qualifiers in the oversight claim. The next round still left a claim with those scope concerns. Draft revision must use the recorded qualifier feedback; lowering verification standards is not a remedy. The two-claim test restriction also limits completeness and does not characterize default production capacity.
4. **Citation filtering removes accurate gap/limitations text.** The model approved 19 units; structural filtering kept five. Inspection of `_verify_report_citations` confirms non-heading prose requires both claim and evidence markers, including process/gap statements, followed by empty-heading removal. This deletes useful limitations. A future fix should render deterministic gap/limitation statements from saved artifacts while preserving strict citations for factual findings. No historical report was rewritten here.
5. **Cache benefit remains unproven.** Exact cache avoided no inference in this run. Do not widen it to semantic reuse of changed evidence merely to increase hit rate. Add miss-reason observability before deciding whether other optimizations are worth their complexity.

## Reservation accounting

| Metric | Recorded amount |
|---|---:|
| Planning allowance, not charged/reserved upfront | $0.80 |
| Hard additional-run allowance | $1.10 |
| Reserved before run | $2.138282 |
| New request reservations | $0.702245 |
| Cumulative reserved | $2.840527 |
| Conservative reservation stop | $3.50 |
| Remaining reservation capacity | $0.659473 |
| Authorized total | $4.00 |
| Confirmed billed charges | Unknown |

There were 22 added reservations: 20 Mesh attempts and two Brave attempts. Each dispatch was preceded by a matching durable reservation event. All 66 earlier ledger entries and authorization history were preserved. No refunds, reset, or cap increase. Reservations use conservative bounds and are not provider invoices. Actual billing, including any discount, remains unknown.

## Post-run verification

Normal `uvicorn app.main:app` entry point restored on runtime `30312f9`; temporary guard mount absent and evaluation lock released. Public health/DB readiness passed. SQLite integrity is `ok`, with 19 saved runs and no active runs. All original 18 run records match the consistent pre-run backup exactly. Public Audit shows 20 calls and zero cache reuses; the new run appears in the sidebar. Desktop screenshot captured; no physical Android evidence added.

Guard/budget tests passed 13/13 in an isolated Linux container before launch. Local backend suite passed 174 tests with one Linux-only skip. Backend/frontend CI for guard source `a88f80b` passed; organizer job remains separate and red while no submission exists. Result documentation commits may have newer pending CI; they do not change runtime.

## Next gate

Action 2 execution/measurement is complete, with negative quality/cache results retained. Remaining $0.659473 is reservation capacity, not a guarantee that all remaining scenarios fit. Confirm scope before Action 3. Prioritize retrieval backfill, explicit search errors, qualifier repair and retention of deterministic limitations before spending on broad scenario tests. No additional paid evaluation or hackathon submission without the required next approval.

## Per-call measurements

All rows are real Mesh responses; local cache false, `request_sent=true`, cached-prompt tokens zero, finish reason `stop`.

| # | Agent | Prompt tokens | Completion tokens | Duration ms |
|---:|---|---:|---:|---:|
| 1 | planner | 229 | 1060 | 8079 |
| 2 | search_strategist | 1429 | 385 | 2688 |
| 3 | researcher | 3204 | 2213 | 9510 |
| 4 | source_critic | 3227 | 926 | 5468 |
| 5 | claim_drafter | 1628 | 837 | 4637 |
| 6 | prosecutor | 810 | 1420 | 7524 |
| 7 | defense | 733 | 1078 | 4646 |
| 8 | judge | 2488 | 1328 | 6454 |
| 9 | coverage_analyst | 1918 | 1800 | 10654 |
| 10 | search_strategist | 2689 | 444 | 3599 |
| 11 | researcher | 3266 | 1550 | 5994 |
| 12 | source_critic | 3290 | 1242 | 8004 |
| 13 | claim_drafter | 1991 | 704 | 4202 |
| 14 | prosecutor | 817 | 1164 | 8107 |
| 15 | defense | 740 | 1004 | 4592 |
| 16 | judge | 2417 | 1808 | 9114 |
| 17 | coverage_analyst | 2069 | 1898 | 7852 |
| 18 | synthesizer | 2113 | 1087 | 5976 |
| 19 | report_verifier | 1060 | 1162 | 5155 |
| 20 | report_verifier | 778 | 1231 | 6651 |
