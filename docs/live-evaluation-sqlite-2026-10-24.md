# Live SQLite evaluation — 2026-10-24

Run: [eval20261024sql01](https://deepdive.example.invalid/run/eval20261024sql01).
Runtime revision: 1c0fbb7ebf04701c699cd2c8ce817e7f9f9e1f0b. Real deployed agent functions, Mesh inference, Brave retrieval and production SQLite persistence; invoked by guarded evaluation process, not browser or n8n. One round deliberately bounds this baseline; it does not test gap recovery.

## Measured execution

END, no warnings/errors. 2 sources, 10 extracted passages, 8 active claims, 8 accepted. 17 successful recorded AI calls; 26,995 prompt + 25,299 completion = 52,294 total tokens; 0/17 calls lack usage metadata. Elapsed to final checkpoint: 154.543 seconds. One Brave request reservation. Conservative combined reservations: $0.573324, retained without refunds; actual billed dollars unverified. User cap $3; evaluation reservation stop $2.50. No direct provider calls used by runner; underlying gateway uses official Mesh endpoint.

## Manual source and section review

All 8/8 accepted atomic claims match their cited passages from SQLite's official [WAL documentation](https://www.sqlite.org/wal.html). This is one reviewer assessing a small, positive technical case; it is not independent double-blind evaluation, external factual accuracy across domains, or contradiction recall.

| Report section | Review | Missing scope |
|---|---|---|
| Executive summary | Main statements supported by cited official passages | Does not establish comprehensive comparison |
| Rollback journal | Copy-before-write mechanism supported | SHARED/RESERVED/PENDING/EXCLUSIVE stages and reader blocking absent |
| WAL read snapshots | End-mark statement supported | wal-index and reader snapshot details incomplete |
| Concurrency differences | Concurrent readers/writer and default 1,000-page checkpoint supported | Rollback blocking comparison and checkpoint effects missing |
| Remaining limitations | Network filesystem and shared-memory claims supported | Single writer, checkpoint starvation and WAL growth omitted |
| Operational constraints | Repeats supported network/shared-memory constraints | Persistence and compatibility details absent |

Coverage: 0/5 subquestions green, 3/5 yellow, 2/5 red. Answer is partial despite 8/8 internal acceptance. Final synthesis includes same-host detail present in its cited source passage but not separately represented as an accepted atomic claim; final prose-to-atomic-claim mapping remains imperfect.

## Proven retrieval bottlenecks

Official source snapshot: 31,727 characters; selected slice 0–7,000. Secondary source: 15,476 characters; selected slice 8,476–15,476. Thus late-page selection operated live, but a single window still omits relevant official text later in the page.

Secondary source contained single-writer evidence but received heuristic trust 0.20 (below configured 0.40), so its passages were excluded from drafting. Official source scored 0.85. No claim-slot exclusions occurred. This omission was caused by trusted-evidence selection plus narrow official extraction, not the claim budget. Source critic only sees the initial 500-character snippet, even when research uses a later selected window; its low relevance score cannot be treated as a full-page review.

Contradiction detection correctly recorded skipped_single_source: accepted/drafted claims link only to the official source. No paid contradiction calls were made. Zero retained contradictions does not show source consensus.

## Next actions

Supply actual selected/extracted content to the source critic; preserve source-quality uncertainty. Evaluate question/subquestion-specific windows across gap rounds while keeping explicit input budgets. Add an uncertainty/false-premise case and a labelled contradictory-source case within the remaining shared reservation budget. Apply the separately tested multi-citation link fix after candidate validation. Do not submit on these results.
