# Live uncertainty and contradiction evaluation — 2026-10-24

Run [eval20261024exo01](https://deepdive.srv1493167.hstgr.cloud/run/eval20261024exo01), runtime f6b375f. Real Mesh/Brave, deployed agent code and SQLite persistence, one round, invoked through guarded process rather than browser/n8n.

## Uncertainty case

Question: What does the published evidence about K2-18 b establish about extraterrestrial life, and what remains unconfirmed?

Measured: END with one warning, 2 source records, 9 passages, 12 active claims, 5 accepted and 7 partially supported/withheld. 24 recorded calls, 48,599 prompt + 44,761 completion = 93,360 total tokens, 0 missing usage records. Elapsed 192.481 seconds. Two malformed synthesis attempts triggered deterministic verified-claim fallback. This is degraded completion, not a clean synthesis pass.

Retrieved journal and arXiv pages are versions of the same study, not two independent studies. Both critics received selected source windows and prompt version source-critic-window-v2. Journal scored 0.72; preprint 0.45. These heuristic scores do not establish calibration or causal improvement over the SQLite case.

Manual review: retained claims have matching source wording; the spectrum/model claim drops the paper's 'we find' attribution and needs more careful study-specific framing. Final report does not claim confirmed life, but does not directly answer the central uncertainty question either. Seven withheld claims include closely matching uncertainty statements, exposing conservative rejection and context/attribution problems. No broad accuracy percentage is claimed. Retrieved evidence omits independent reanalyses and competing atmospheric interpretations. The report is incomplete and cannot pass a complete-answer gate.

Source checking uses the actual study [arXiv abstract](https://arxiv.org/abs/2504.12267) and [journal page](https://iopscience.iop.org/article/10.3847/2041-8213/adc1c8). These report one team's interpretation, not field-wide consensus.

## Labelled synthetic detector baseline

Three deliberately fictional two-source cases were passed through the real detector and Mesh gateway, without retrieval or synthesis:

| Case | Expected | Retained | Outcome |
|---|---|---|---|
| Same entity, metric, units and fiscal year; 10 vs 20 million | Conflict | 0 | Miss |
| Different fiscal years; 10 vs 20 million | No conflict | 0 | Pass |
| Same period and amount | No conflict | 0 | Pass |

The positive model response contained a conflict candidate, but its evidence arrays contained passage text instead of IDs; strict validation rejected it. Detector baseline sensitivity on this single positive is 0/1, false-positive count on two negative controls 0/2. This tiny synthetic component set is not real research precision/recall.

Local correction explicitly requires evidence IDs copied from input, distinguishes claim text from evidence-ID arrays, and keeps strict validation. Prompt version contradiction-evidence-ids-v3. All 128 backend regressions pass (3.24 seconds); live retest and deployment of this correction remain pending. Do not present baseline as fixed.

Shared reservations after two research runs and three detector calls: $1.492385. No refunds; actual billed charges remain unverified. User authorized $3 combined; guard stops before $2.50 reserved. No hackathon submission.


## Corrected detector retest (candidate 3d4dc19)

The same three labelled fixtures were rerun through real Mesh using isolated candidate source before deployment. Same-period conflict retained one contradiction; different-period and agreement controls retained none: 3/3 expected outcomes. Baseline remains recorded above. This is one positive and two negative synthetic cases, not broad contradiction precision/recall. Strict evidence-ID filtering remains enabled. Shared conservative reservations after this retest: $1.585772; actual billing unverified. Candidate backend suite remains 128 passed. Production remains f6b375f pending rollout.

Synthesis diagnostics established finish_reason=length and 4,096 completion tokens on both failed attempts, with identical request/output hashes. Candidate compact synthesis limits report length; length-retry guidance now changes the request and its audit hash while retaining the token ceiling. Saved-claim synthesis replay is pending; original research record will not be overwritten.


Synthesis replay completed: one successful Mesh call, finish_reason=stop, 4,990 total tokens; compact JSON parsed. Original run was not overwritten. Combined reservations now $1.620532. Manual report review still finds additions beyond the accepted atomic claims (notably 3-sigma detail carried from a passage associated with an accepted abundance claim, although its dedicated significance claim was withheld). Link validation permits these clauses because IDs are valid. Structural recovery therefore passed; final report atomic-claim grounding did not pass a complete semantic gate. Do not describe this replay as full correctness.
