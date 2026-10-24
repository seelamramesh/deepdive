# DeepDive quality release evidence — 2026-10-24

Runtime revision: `9c9180df011624830b45b9632a6a246896b7ce24`.
Image: `deepdive:quality-20261024t161607z`. Both values were independently read from the running production container after deployment. Documentation-only commits after this revision do not imply a new runtime deployment.

## Verified release gates

- Linux candidate: 116 backend tests passed, one existing deprecation warning, 1.76 seconds. Six integrations mock provider/search/fetch I/O; they do not measure live model accuracy.
- Frontend: 22 tests, TypeScript and production build passed. Large-bundle warning remains.
- Consistent SQLite backup: 15 saved runs; all 15 run IDs preserved after rollout. Database health passed at `/app/data/deepdive.db`.
- Existing report text and original coverage assessment unchanged. Derived accepted-claim counts for run `8f567d3d99df44ff`: `[0, 0, 3, 2, 0]`.
- Coverage, Contradictions and Control Flow checked at 360/375/390/412px: 12 responsive-browser checks, no page overflow. Physical Android device testing remains outstanding.
- No paid research runs started by the agent for this release.

Backup: `/docker/deepdive-quality-20261024T161607Z/validation-data/deepdive.db`.
Rollback container: `deepdive-rollback-ui-20261024161807`.

## Public repository and CI

[Draft PR #1](https://github.com/seelamramesh/deepdive/pull/1) contains the runtime revision on branch `codex/research-audit-20261024`; main is not merged.

[Application CI](https://github.com/seelamramesh/deepdive/actions/runs/40110803648): backend and frontend passed on 9c9180d.

[Organizer workflow](https://github.com/seelamramesh/deepdive/actions/runs/40110767698): 4/4 critical checks passed, but reporting returned HTTP 403 because no hackathon submission entry exists. Overall workflow failed; organizer result was not recorded. Submission remains intentionally on hold. The official workflow was not changed.

## Remaining limits

Shared architecture text is common across searches; actual recorded queries, evidence and events differ by run. Historical missing contradiction diagnostics are unavailable, not reconstructed. The new contradiction comparison policy has deterministic regression coverage but no fresh live model accuracy measurement.

Final report citation-ID checks do not prove every sentence is entailed by its sources. Source extraction currently uses the first 7,000 characters; challenge pages and later-page relevant material remain quality risks. No vector database is implemented. Observed token records are not a transactional billing ledger; dollar costs remain unknown without verified account rates. Expanded labelled live evaluations and section-by-section review remain outstanding; a numeric paid-test cap or explicit bounded scope is still needed.
