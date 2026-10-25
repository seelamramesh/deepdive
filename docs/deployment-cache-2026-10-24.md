# Cache release evidence — 2026-10-24 America/Chicago

## Runtime and scope

Production image `deepdive:cache-30312f9`, OCI revision `30312f9f12a1fdd0c5fb9e5ca51255eb9e8b8900`. Deployment completed at 2026-10-25 00:17 UTC (October 24 locally). Documentation commits after this revision do not change the deployed runtime.

Action 1 of the final gaps prompt is complete. Actions 2 onward await confirmation as requested in that prompt. No hackathon submission or main-branch merge was performed.

## Evidence

| Check | Observed result |
|---|---|
| Local backend | 170 passed |
| Exact image Linux backend | 169 passed, 1 skipped; repeated immediately before promotion |
| Skipped test | Node-dependent workflow expression test; covered in local suite |
| Frontend | 27 passed across 4 files |
| Production build and TypeScript | Passed; dashboard chunk remains 665.42 kB minified |
| Isolated candidate | Separate copied SQLite DB, no public routing |
| Browser cache fixture | Explicitly synthetic events, copied DB only; cached badge and 0 incremental tokens visible |
| Responsive browser | No page overflow at 360, 375, 390, 412 and 1440 px in cache Audit view |
| Historical browser state | Cache data unavailable; no invented zero-hit history |
| Backup | SQLite backup API, integrity verified; 18 runs |
| Promotion guard | No active/interrupted runs at staging and final pre-promotion check |
| Independent public API | Health OK, DB OK, 18 runs, saved report readable, nullable cache fields exposed |
| Preservation | Every saved run JSON equals consistent pre-promotion backup; no synthetic fixture in production |
| Persistent data | `/docker/deepdive/data` mounted at `/app/data` |

Browser checks used responsive desktop emulation, not physical Android. Screenshot capture API failed twice; DOM/accessibility evidence was saved instead. Mermaid source was reviewed against implementation; independent rendered-diagram inspection remains pending.

## Rollback

Previous production container retained as `deepdive-rollback-ui-20261025001710`, using `deepdive:prejury-03e239a`.

Consistent backup: `/docker/deepdive-cache-final-30312f9/validation-data/deepdive.db`.

Two rollback checks passed: an automated simulated public-readiness failure exercises removal of the failed replacement and restoration of the old container; a separate previous-image container starts against an independent copied database and serves health plus copied run records. No forced live rollback drill was performed. A real rollback requires checking active runs before switching containers; keep the persistent mount and current database.

## CI

For runtime revision `30312f9`, [backend/frontend checks passed](https://github.com/seelamramesh/deepdive/actions/runs/40145779383). [Organizer job](https://github.com/seelamramesh/deepdive/actions/runs/40145776043) passed all four critical checks, then failed reporting with HTTP 403 because no hackathon submission entry exists. Do not submit merely to clear this check. Full CI is not green.

## Cost and limitations

No new paid research was launched for these checks. Preserved evaluation ledger: $4 authorized total, $3.50 conservative reservation stop, $2.138282 reserved, $1.361718 remaining reservation capacity. Actual billed charges unknown. Organizer CI separately verifies key validity; this is not a measured research evaluation.

Live cache hit rate, token savings, latency savings and billing discounts remain unmeasured. Public n8n requests are not automatically guarded by the evaluation reservation helper. Next action must install/verify per-request budget reservation before launching a bounded n8n evaluation. Historical report inaccuracies, including the Geotab example, remain recorded and unchanged.

## Updated documentation

[Simple flow guide](FLOW-README.md) covers question-to-report stages, caching, n8n, example, UI views and storage. [Architecture](../README.md#architecture) shows Python orchestration, twelve Mesh AI roles, exact cache, snapshots, SQLite and final report checks. SQLite stores serialized run artifacts; the data diagram is conceptual, not a set of SQL relationship tables. No vector DB exists.
