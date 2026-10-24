# User n8n run validation — 2026-10-24

Run: https://deepdive.srv1493167.hstgr.cloud/run/c324ed4de85d4e3c
Question: What are the main risks of investing in EV batteries in 2026?

Decision: do not submit yet. This review started no new research and changed neither production nor the workflow.

## Verified results

- Production health and persistent database readiness passed.
- n8n execution 414787 belongs to workflow vXuzyMGtoaIr2Gcu and started exactly c324ed4de85d4e3c. Saved execution status success. Get Report, Get Certificate and Respond Success actually executed; Respond Failed did not. Read-only execution database fallback was used because the connector's advertised get_execution tool returned Tool not found.
- Execution duration 317.583 seconds; research duration 315.277980 seconds. Three research rounds, 3 source records, 14 passages, 12 active claims, 10 accepted, zero retained contradictions and no saved warning/error.
- Forty recorded successful AI calls: 85,372 prompt + 66,630 completion = 152,002 total tokens. All 40 have token metadata. Actual dollar billing remains unknown. This user-started run was not launched through the separate evaluation reservation guard.
- Final report references 10 accepted claim IDs and 6 real evidence IDs, with no unknown IDs. This establishes citation identifier integrity, not factual currency, completeness or every sentence's entailment.

## Submission blockers and quality risks

1. Production remains image deepdive:scoring-20261024-r1, revision f6b375f071a3ec6e144a1ca0a754ca9ae6d2effb. New report verifier, compact synthesis retries, contradiction ID correction, gap-window policy and material grouping from PR branch are not deployed. report_grounding_status is absent and report_grounding_audit empty; no report_verifier calls exist in the run.
2. Coverage is 0/5 green, 1/5 yellow and 4/5 red. Technology, demand, policy/geopolitics and operational/financial coverage remain thin or missing. No primary-source records are counted in coverage. Original report acknowledges some gaps; END is not completeness.
3. Battery degradation cites a secondary site's 1.8% without identifying its historical study year. Geotab's January 13, 2026 primary release reports 2.3% for an updated sample of more than 22,700 EVs, explicitly contrasting 1.8% in 2024. Historical 1.8% is not inherently false; using it without date/scope in a 2026 report is a currency/attribution problem.
4. The secondary source also claims LFP-specific 1.2–1.5% annual degradation. The inspected Geotab 2026 primary release does not corroborate that chemistry-specific range; its approximately 1.5% comparison concerns primarily AC/lower-power charging. Do not label the chemistry claim externally verified from that release.
5. Final synthesis adds risk implications beyond accepted atomic statements. Claim/evidence IDs cannot alone verify causal or investment implications. New reviewer is required to evaluate such prose, and still cannot guarantee external truth.
6. Contradiction audit reports 22/32 scheduled cross-source candidate pairs compared in round 3, with 10 unchecked under budget. Zero retained contradictions does not establish consensus. Earlier rounds repeated selected windows for reused sources; new gap-round behavior was not exercised on this older backend.

Primary fact-check sources:
- https://www.geotab.com/press-release/ev-battery-health-degradation-fast-charging-study/
- https://www.geotab.com/uk/press-release/2024-battery-degradation/

## Wait configuration correction

Earlier review incorrectly generalized legacy Wait v1 defaults (one hour) to v1.1. Installed source has version-specific overrides: Wait v1.1 defaults amount=5 and unit=seconds. Active workflow has empty Wait parameters but typeVersion 1.1; that alone is not a one-hour delay defect. Execution snapshot explicitly specified resume=timeInterval, amount=5, unit=seconds; 63 saved visits lasted 5000–5002ms. Explicit parameters remain useful for clarity, but no delay fix is required to explain this run.

Current published workflow is active with 14 nodes; validation expressions include string guards. Changing n8n JSON does not deploy FastAPI backend code.

## CI snapshot

PR runtime candidate revision 24d69ea19b5896cf46b447573b710eaf9512b24e: backend and frontend checks passed. Organizer workflow ran 4/4 critical checks successfully but reporting returned 403 because no submission entry exists; overall organizer job failed and result was not recorded. Do not submit only to make that check green.

Application CI: https://github.com/seelamramesh/deepdive/actions/runs/40117283182
Organizer CI: https://github.com/seelamramesh/deepdive/actions/runs/40117278212

## Next steps before submission

1. Safely validate/deploy the candidate backend and UI on an exact revision, with Linux tests, copied SQLite backup, no active runs, browser checks and rollback.
2. Retest through n8n against that deployed revision, with primary Geotab/market/regulatory evidence and explicit study dates. Target the four red areas and retain shortcomings honestly.
3. Evaluate report-review exclusions, genuine contradictions, malformed/failure/timeout paths and latest mobile controls; preserve original runs rather than rewriting their outcomes.
4. Update final jury architecture, examples and self-evaluation to match measured deployed behavior. Keep submission on hold until the remaining gates pass and the user approves.

Artifacts: DeepDive-User-Run-c324ed4de85d4e3c-workspace.json and DeepDive-n8n-RunValidation-c324ed4de85d4e3c.json in this chat's outputs folder. No new paid calls or submission performed.
