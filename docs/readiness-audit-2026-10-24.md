# DeepDive readiness audit — 2026-10-24

Status: incomplete overall; latest runtime revision `1c0fbb7ebf04701c699cd2c8ce817e7f9f9e1f0b` is deployed as `deepdive:extraction-20261024-r1` (image and revision independently rechecked over SSH). See [release evidence](release-evidence-2026-10-24.md). Phase 1 mobile UI and tested hardening were deployed after the user authorized proceeding with Phase 1 and the goal. No submission performed. This is a fresh audit, not a replacement of historical measured results.

## OODA evidence and action

- Observe: read-only export of 14 production workspaces found 554 recorded response records, 8 unsuccessful responses, no recorded total-token values and no retrieval traces. No read failures.
- Orient: runtime inspection confirmed production already has prompt/completion/total-token model fields and gateway response-usage extraction. The container started at 2026-10-24T14:06:24.484975438Z; the newest stored run was created at 2026-10-24T06:18:10.316349+00:00. Therefore absence of usage in those historical records does not prove a defect in the currently deployed recording code. Do not invent a root cause or reconstruct historical consumption.
- Decide: test known local gaps offline before spending: missing failure-path usage records, hidden SDK retries, arguments-only judging, invented defense quotes and inconsistent evaluation thresholds.
- Act: reproduce six failures, implement focused corrections, and run deterministic integrations plus the full backend suite. A later authorized rollout published image deepdive:mobile-20261024t153739z after isolated validation; no paid research was started by the agent.

## Proven local improvements

1. Judge receives original cited passages and evidence IDs. Both newly generated and supplied defense mappings are filtered against real cited evidence with whitespace-only normalization. Quote membership is not a proof of semantic entailment.
2. A claimed evidence ID absent from stored/supplied evidence cannot yield an accepted Supported verdict. Unknown contradiction evidence IDs are removed.
3. Mesh client rejects non-official/insecure inference endpoints. Provider credentials remain backend-only. SDK-internal retries are disabled; existing bounded JSON retries are retained and audited. Tradeoff: transient transport errors now fail immediately rather than being retried invisibly.
4. Transport failures/cancellation retain an unsuccessful attempt record with unknown usage and a safe error type. Empty/malformed completion responses retain provider usage metadata, including known zero. These are observed-call records, not a transactional billing ledger.
5. Orchestrator checkpoints now include observed calls, making persisted usage available before terminal completion. Cooperative task cancellation saves an explicit Failed state. Abrupt process death or cancellation during database writes can still leave gaps; automatic continuation is not implemented.
6. Evaluation uses the run's saved confidence threshold. Certificates derive prompt versions from actual calls; Judge records `judge-grounded-v2`. Previously emitted certificates are not rewritten.

7. Sources retain exact sanitized snapshots. New retrieval avoids extraction refetch; repeated source URLs reuse stored content within a run. Tampered/missing snapshots are withheld. Full source snapshots remain server-side; workspace responses exclude them. Extraction records distinguish full-snapshot hashes from hashes of the 7,000-character slice.

## Fresh test results

Full backend suite: **104 passed**, one existing Starlette/httpx deprecation warning, pytest summary 2.92 seconds. Machine-readable result: `evaluations/offline-regressions-2026-10-24.json`. Frontend Control Flow explanations were updated to match current snapshot/judge behavior. Fresh frontend verification: 18 tests passed; Vite production build and TypeScript passed. Existing large-chunk warning remains.

Six deterministic API → real agent functions → real gateway parsing/audit → orchestrator → SQLite → workspace integrations passed:

| Fixture | Checked behavior |
|---|---|
| supported_and_withheld | One supported fixture claim retained; altered-number claim withheld; original passage reaches Judge; usage persists |
| gap_then_recover | Thin coverage leads to a second research round and explicit RESEARCH_GAPS transition |
| malformed_synthesis | Two malformed response attempts are recorded, then verified-claim fallback report is produced with warning |
| no_sources | Terminal report explicitly states insufficient verified evidence; no accepted claims fabricated |
| tampered_snapshot | Snapshot/hash mismatch blocks extraction and leads to explicit insufficient-evidence outcome |
| long_snapshot | Full snapshot and the 7,000-character extraction slice have correctly distinguished hashes |

Provider/search/fetch I/O is mocked. Fake response metadata uses fixed token values solely to exercise persistence. **These are not real token consumption, live research accuracy, semantic precision/recall or billing measurements.** The fake judge's verdicts are scripted; this validates plumbing and guards, not an LLM's judgement quality.

## Requirement-by-requirement status

| Attached hackathon requirement | Current evidence | Limit |
|---|---|---|
| All AI through Mesh | Architecture tests pass; single gateway; new local runtime allowlist rejects other endpoints | Runtime guard included in deployed candidate; do not equate a static scan with full live packet capture |
| At least three distinct agents | Distinct agent functions/prompts; existing historical agent records | No new paid multi-agent execution in this audit |
| Real retrieval with source provenance | Historical workspaces contain sources/evidence; retrieval code inspected | Local sources now retain immutable sanitized snapshots; extraction slice hashes and evidence snapshot hashes are tested. Historical runs lack snapshots; live retest pending |
| Claims checked against cited sources | Local Judge now sees actual passages; unknown IDs/invented quotes rejected by regression tests | Real model entailment accuracy requires a new labelled live evaluation |
| Thin areas trigger more research | Real orchestrator loop exercised by offline integration; historical rounds also exist | Scripted coverage fixture does not prove live coverage calibration |
| Grounded structured reports | Report/citation guards and fallback exercised | Final citation validation establishes allowed IDs, not complete sentence-level entailment; unsupported prose remains a review risk |
| Auditable kept/rejected decisions | Claims/verdicts, coverage, state transitions, traces and calls | Historical missing telemetry cannot be backfilled honestly; source trust is heuristic |
| Self-evaluation/test set/numbers in repo | Historical evaluation docs plus new six-fixture integration and latest 116-test result | Expanded live diverse question set and independent passage review remain pending |
| Public repo/README/dependencies/ignored secrets | Existing local files and prior remote history | Revision 9c9180d is pushed on codex/research-audit-20261024; draft PR #1 exists. Application backend/frontend CI passed; organizer reporting failed because no submission entry exists |
| Optional contradiction detection | Existing implementation/tests/historical records | Strong live contradictory-source fixture still needed; lack of detected contradictions is not consensus |
| Optional export/follow-up | Existing page/print/follow-up routes and mobile work | No new live follow-up evaluated here |
| n8n compatibility | Existing summary contract unchanged, 14-node JSON retained | Summary contract preserved in deployment; no new live n8n research execution |

The vector database named in the suggested stack is not an implemented component. Do not depict SQLite as a vector DB or claim vector retrieval.

## Later live observations and release

A newly completed existing run, 8f567d3d99df44ff, has 48 recorded calls with provider usage: 65,738 input + 63,117 output = 128,855 total tokens. Two logical searches are traced. This establishes recorded token metadata for that run, not billing completeness. The original 554 response records remain unpriced and lack usage. No new paid run was started by the agent.

The live report is partial: 5 accepted claims, 12 active claims, 17 evidence passages and 5 source records. Two records contain browser challenge pages. The original recorded coverage reports zero verified claims in every row despite five accepted claims; the deployed workspace now derives counts [0, 0, 3, 2, 0] and preserves that original assessment separately. The earlier code capped retained claims by earliest entries; deployed allocation now protects accepted claims and balances remaining slots across topics, with explicit exclusion records. The complete second draft is not persisted, so discarded medical claims cannot be reconstructed or asserted.

Mobile release: deepdive:mobile-20261024t153739z, backup /docker/deepdive-candidate-20261024T153739Z/validation-data/deepdive.db, rollback deepdive-rollback-ui-20261024153914. All 15 run IDs were preserved. Physical Android testing remains outstanding; Chromium responsive checks covered 360/375/390/412/480px and all seven views. See the delivered Android deployment report and screenshots for detailed evidence.

## Remaining work before completion

### Latest deployed quality release

Local backend suite now has **116 passing tests**; frontend **22 tests plus build/TypeScript pass**. The same 116 backend tests passed in the Linux deployment candidate (1.76 seconds); earlier counts above describe historical releases. Coverage counts now derive from stored sources/evidence/threshold-qualified judgements, missing subquestions remain visible, and green status is blocked without accepted support. Contradiction comparison now skips single-source claim sets, covers candidate pairs across former six-claim/topic boundaries within a three-call-per-round default budget, filters invalid/same-source results, and records checked/uncompared/rejected counts. UI displays those diagnostics and recorded detector-token subtotals; historical missing diagnostics stay unknown. These are mocked-I/O regressions, not a new live model-accuracy evaluation.

The shared “How commands travel” explanation is now explicitly labelled as shared architecture in local UI. Run-specific queries, evidence and events remain separate; browser API requests remain session-wide. These label and diagnostic changes passed candidate validation and are deployed at revision 9c9180d. A separate reviewer reproduced duplicate source-pair counts under reworded topics and silent truncation of a fourth candidate; both were fixed and regression-tested. Historical coverage is now derived on read while preserving the original assessment separately, without changing stored research records. Claim-slot allocation now retains accepted claims and balances remaining slots across topics, recording budget exclusions and prior judgements. Final prose grounding remains open.

1. Confirm a numeric combined Mesh/Brave spend cap, or an explicit bounded live test scope. Current acknowledgement supplied no numeric cap; no paid tests were launched here.
2. Obtain verified account-specific pricing/billing information before displaying dollar estimates. Token fields alone cannot establish charges, BYOK fees or cached-token billing.
3. Retest the new deterministic counts, balanced claim allocation and snapshot behavior with live retrieval; address final prose grounding and expand labelled positive, mutation, contradiction and temporal-scope cases.
4. Completed rollout validation for latest quality release: 116 backend tests on a copied database, 22 frontend tests/build, backup integrity, 15 preserved run IDs, public readiness and 12 checks across the three changed mobile views. The preceding mobile release separately had 35 view combinations checked. Test any subsequent fixes separately; this does not establish complete application correctness.
5. Confirm new live token metadata and search traces, perform section-by-section manual evidence review, and report actual results with denominators and limitations.
6. Review draft PR #1 and keep release/jury documents consistent with the deployed runtime. Application CI passed on runtime revision 9c9180d; organizer reporting remains blocked by the deliberately absent submission entry.
7. Keep submission on hold until the user explicitly authorizes it after validation. Passing automated organizer checks alone does not prove claim correctness or complete submission.

Goal remains active. Deployment of the named revision is verified. Hackathon readiness, complete feature coverage and submission success are not established.


## Subsequent extraction-window release — deployed

The first-slice cutoff was reproduced with a source containing relevant text after character 7,000. A bounded lexical selector now scores overlapping contiguous windows against the original question, prioritizes distinct matching terms, caps repeated-term contributions and uses the earliest window on ties. Short/no-match sources keep their original first-slice behavior. The same immutable source snapshot is used; extraction audit records actual start/end offsets, slice hash and `query_lexical_window_v1`. Character budget remains 7,000 per source; no additional AI calls are introduced.

Fresh local backend result: 120 passed, one existing deprecation warning, 3.09 seconds. A seventh mocked end-to-end fixture proves late-page content reaches the researcher and persisted report with correct source offsets. This includes late-page, tie/no-match, Unicode/short-source and invalid-budget checks plus six existing mocked end-to-end integrations. No paid calls or new live quality measurements. The selector is a heuristic: it can miss synonyms or relevant context outside the chosen window. Subsequent candidate validation passed 120 backend tests on Linux in 2.42 seconds. Deployed image `deepdive:extraction-20261024-r1`, runtime revision `1c0fbb7ebf04701c699cd2c8ce817e7f9f9e1f0b`; public readiness and 15-run listing independently verified. Backup: `/docker/deepdive-extraction-20261024-r1/validation-data/deepdive.db`; rollback: `deepdive-rollback-ui-20261024163017`. Frontend unchanged; prior tested build reused from Docker cache. No new live model accuracy result.


## Active guarded live evaluation and subsequent local citation fix

User authorized up to $3 combined Mesh/Brave spend. Single live run `eval20261024sql01` is executing under a $2.50 conservative reservation stop, using twice observed maximum catalog text rates plus an input overhead allowance and twice public Brave request pricing. Reservations are retained after failures and unknown usage; they are not invoice-confirmed charges. This is an evaluation-process guard, not an application-wide billing cap.

A new local regression reproduced partially unlinked multi-citation lines surviving when any one pair was approved. The corrected guard requires each claim reference to have an approved cited evidence link and each evidence reference to have an approved cited claim link. A fully linked multi-claim positive case remains allowed. This is link integrity, not semantic entailment. Local backend suite: 128 passed, one existing warning (3.19 seconds before the additional positive assertion). This citation fix is not deployed; do not redeploy while the live evaluation is active.


## Source-critic window correction (candidate)

Seven end-to-end fixture assertions now require the critic to receive the selected immutable window with exact offsets/hash, the original question and a partial-window scope label. Missing/tampered snapshots are excluded from scoring as well as extraction. New prompt version `source-critic-window-v2` separates opening snippet from selected content, relevance from authority and unknown dates from inferred recency. Local suite: 128 passed, one existing warning, 3.06 seconds. This does not prove improved model calibration; live retest is still needed. A second guarded uncertainty case shares the existing reservation ledger rather than resetting the budget.
