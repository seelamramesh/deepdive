# Measured Evaluation Results

Date: 2026-10-18. Environment: production deployment at `deepdive.srv1493167.hstgr.cloud`. Each run used two research rounds. Results below come from persisted run artifacts and `/runs/{id}/evaluation`; no score is invented.

## Questions

1. **EV battery risk:** “What are the main risks of investing in the EV battery market in 2026, and which claims are disputed across credible sources?”
2. **AGI claim audit:** “Has artificial general intelligence been achieved as of October 2026? Separate documented capabilities from unsupported public claims and identify missing evidence.”

## Results

| Measure | EV battery (`2ed2c8150b91476e`) | AGI (`0d67c451657b4525`) |
|---|---:|---:|
| Terminal state | END | END |
| Sources | 6 | 4 |
| Evidence passages | 34 | 19 |
| Drafted claims | 12 | 12 |
| Supported claims | 6 | 5 |
| Rejected claims | 6 | 7 |
| Successful distinct agents | 11 | 11 |
| Valid citation links | 7/7 | 5/5 |
| Evidence-to-source integrity | 100% | 100% |
| Coverage (green/yellow/red) | 1/1/4 | 0/1/4 |
| Contradictions retained | 0 | 0 |
| Non-empty report | Yes | Yes |
| Warnings | Source-critic JSON truncation in round 2; last verified checkpoint used | None |

## Regression Found and Fixed

Initial EV run `4142fd35d392462b` ended safely but produced 1 low-trust source, 6 evidence passages, and 0 claims. Root cause: bounded search selected multiple queries for one subquestion, starving other sections. Query selection now spreads searches across subquestions and adds deterministic fallback queries when Mesh omits a subquestion. Retest increased retrieved sources from 1 to 6 and verified claims from 0 to 6.

Round-2 EV source scoring then exposed JSON truncation when six sources were sent in one Mesh call. Source Critic now processes batches of three. A non-mutating production replay on the same six stored sources scored 6/6 successfully with no missing source IDs. This validates batching against Mesh without another Brave search, but it does not rewrite the historical run warning.

## Honest Limits

- EV report remains partial: four of six sections are red, and no contradiction survived validation.
- AGI report remains partial: four of five sections are red.
- Citation integrity proves references resolve to stored evidence; it does not independently prove real-world truth.
- Mutation test-case generation and metric computation are tested, but no live Mesh mutation score has been measured. Certificate field remains `null`.
- Three two-round production runs were executed. Audit records retain six search-query entries total. Configuration permits up to two Brave requests per round, so provider-side usage can be as high as 12 requests; Brave dashboard is authoritative for billing.
