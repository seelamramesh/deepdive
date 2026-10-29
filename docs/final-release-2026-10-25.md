# Final release verification — 2026-10-25

## Released revision

Runtime and tested source: `ef0382dd8480b7f8ce2c1e5e7ee1650c8958a65f`.
Image: `deepdive:final-ef0382d`.
Normal uvicorn entry point restored; evaluation wrapper is not production entry point.

- Local backend: **214 passed, 1 skipped** (fcntl unavailable on Windows).
- Isolated Linux image: **214 passed, 1 skipped** (image lacks Node for the optional workflow-JavaScript test; local/CI cover the workflow separately).
- Frontend: **30 passed**; Vite and TypeScript build passed locally and in image build.
- Existing Starlette/httpx deprecation and approximately 668 kB dashboard-chunk warning remain; no claim of warning-free build.
- Fresh consistent SQLite backup verified 20 runs and integrity `ok` before promotion.
- Post-release all 20 exact stored JSON hashes match both backup and initial audit export.
- Evaluation ledger SHA-256 unchanged; no new paid Mesh or Brave inference/search calls during final pass.
- Public `/health` returns `ok`, `db_ok:true`, database `/app/data/deepdive.db`; report SPA loads.
- During container replacement the browser briefly observed a 404 routing transition. Public readiness subsequently passed; this is not a zero-downtime deployment claim.

Backup: `/docker/deepdive-final-ef0382d/validation-data/deepdive.db`.
Rollback retained: `deepdive-rollback-ui-20261025055908`.
Deployment log: `/docker/deepdive-final-ef0382d/promote.log`.
A rollback must first check for newly active runs and preserve any new data; do not blindly replace a live database.

## Released UI verification

Actual innerWidth 360, 375, 390 and 412 px: all seven views switched, no page-level horizontal overflow, no visible button/input/select/summary target below 44 px in the sweep. The 412 px test used an override of 411 because browser scaling yielded 412 actual pixels. An earlier sweep accidentally remained desktop after other tabs were created; those measurements were discarded and repeated in a newly bound research tab, checking actual width each time.

Mobile drawer opens, scrolls, closes, and long questions display fully at 16 px with no line clamp. Audit body samples are 16 px. Audit shows three cache reuses, the historical HTTP 422 and the internal certificate. Desktop 1280 px tab switching and report limitations were checked. Keyboard arrow tabs and opening/closing New research were exercised without starting research. Physical Android/notch and live cancellation remain untested.

The numeric audit display has a frontend unit test; historical production runs are not rewritten just to populate the new field. Numeric filtering is demonstrated using the copied Action 3 fixture, not a new paid live run.

## Exact source CI

[Application CI ef0382d](https://github.com/seelamramesh/deepdive/actions/runs/40167403789): backend and frontend jobs succeeded. [Organizer job ef0382d](https://github.com/seelamramesh/deepdive/actions/runs/40167400600): 4/4 critical checks passed, then report recording failed HTTP 403 because no submission entry exists. This is a failed organizer workflow with unrecorded results. The official workflow was not weakened or changed.

[Draft PR #1](https://github.com/seelamramesh/deepdive/pull/1) remains unmerged. Follow-on documentation commits do not change the deployed application revision; their CI must be reported separately.

## Submission handoff

See [final readiness review](final-readiness-2026-10-25.md), [simple flow](FLOW-README.md), and [Action 3 measured evaluation](action3-evaluation-2026-10-25.md).

Code is deployed and final offline bug fixes are tested. Research completeness remains partial; this is not proof of every feature/scenario. No extra paid accuracy test was run. User must decide whether disclosed limitations are acceptable, then explicitly authorize final submission. Organizer recording can be retried only after an entry exists. No submission or merge was performed.
