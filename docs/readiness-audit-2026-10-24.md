# DeepDive readiness audit — 2026-10-24

Status: incomplete overall; Phase 1 mobile UI and tested hardening were deployed after the user authorized proceeding with Phase 1 and the goal. No submission performed. This is a fresh audit, not a replacement of historical measured results.

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
| Self-evaluation/test set/numbers in repo | Historical evaluation docs plus new six-fixture integration and 104-test result | Expanded live diverse question set and independent passage review remain pending |
| Public repo/README/dependencies/ignored secrets | Existing local files and prior remote history | New local work is uncommitted/unpushed; this audit did not verify a new GitHub CI run |
| Optional contradiction detection | Existing implementation/tests/historical records | Strong live contradictory-source fixture still needed; lack of detected contradictions is not consensus |
| Optional export/follow-up | Existing page/print/follow-up routes and mobile work | No new live follow-up evaluated here |
| n8n compatibility | Existing summary contract unchanged, 14-node JSON retained | Summary contract preserved in deployment; no new live n8n research execution |

The vector database named in the suggested stack is not an implemented component. Do not depict SQLite as a vector DB or claim vector retrieval.

## Later live observations and release

A newly completed existing run, 8f567d3d99df44ff, has 48 recorded calls with provider usage: 65,738 input + 63,117 output = 128,855 total tokens. Two logical searches are traced. This establishes recorded token metadata for that run, not billing completeness. The original 554 response records remain unpriced and lack usage. No new paid run was started by the agent.

The live report is partial: 5 accepted claims, 12 active claims, 17 evidence passages and 5 source records. Two records contain browser challenge pages. Coverage reports zero verified claims in every row despite five accepted claims; count derivation needs correction. Code also caps the retained claim list by its earliest entries, which can prevent later-round evidence from receiving active claim slots. The complete second draft is not persisted, so discarded medical claims cannot be reconstructed or asserted.

Mobile release: deepdive:mobile-20261024t153739z, backup /docker/deepdive-candidate-20261024T153739Z/validation-data/deepdive.db, rollback deepdive-rollback-ui-20261024153914. All 15 run IDs were preserved. Physical Android testing remains outstanding; Chromium responsive checks covered 360/375/390/412/480px and all seven views. See the delivered Android deployment report and screenshots for detailed evidence.

## Remaining work before completion

### Next-release work in progress (not deployed)

Local backend suite now has **116 passing tests**; frontend **22 tests plus build/TypeScript pass**. These do not replace the earlier deployed-release counts above. Coverage counts now derive from stored sources/evidence/threshold-qualified judgements, missing subquestions remain visible, and green status is blocked without accepted support. Contradiction comparison now skips single-source claim sets, covers candidate pairs across former six-claim/topic boundaries within a three-call-per-round default budget, filters invalid/same-source results, and records checked/uncompared/rejected counts. UI displays those diagnostics and recorded detector-token subtotals; historical missing diagnostics stay unknown. These are mocked-I/O regressions, not a new live model-accuracy evaluation.

The shared “How commands travel” explanation is now explicitly labelled as shared architecture in local UI. Run-specific queries, evidence and events remain separate; browser API requests remain session-wide. These label and diagnostic changes are pending candidate validation and deployment. A separate reviewer reproduced duplicate source-pair counts under reworded topics and silent truncation of a fourth candidate; both were fixed and regression-tested. Historical coverage is now derived on read while preserving the original assessment separately, without changing stored research records. Claim-slot allocation now retains accepted claims and balances remaining slots across topics, recording budget exclusions and prior judgements. Final prose grounding remains open.

1. Confirm a numeric combined Mesh/Brave spend cap, or an explicit bounded live test scope. Current acknowledgement supplied no numeric cap; no paid tests were launched here.
2. Obtain verified account-specific pricing/billing information before displaying dollar estimates. Token fields alone cannot establish charges, BYOK fees or cached-token billing.
3. Retest the new deterministic counts, balanced claim allocation and snapshot behavior with live retrieval; address final prose grounding and expand labelled positive, mutation, contradiction and temporal-scope cases.
4. Completed rollout validation for current release: 104 backend tests on a copied database, 18 frontend tests/build, backup integrity, 15 preserved run IDs, public readiness and 35 mobile view combinations. Test any subsequent fixes separately; this does not establish complete application correctness.
5. Confirm new live token metadata and search traces, perform section-by-section manual evidence review, and report actual results with denominators and limitations.
6. Commit/push only authorized reviewed changes and verify CI on that revision; publish updated jury documents that match the deployed build.
7. Keep submission on hold until the user explicitly authorizes it after validation. Passing automated organizer checks alone does not prove claim correctness or complete submission.

Goal remains active. No claim of hackathon readiness, complete feature coverage, deployment or submission success is made.
