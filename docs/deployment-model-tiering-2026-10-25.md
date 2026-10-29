# Model-tiering production deployment — 2026-10-25

**Deployed successfully at 2026-10-25 11:16:51 CDT.** Source revision `dfd15d6848f9e464b095ebcde7eb7022d36be8dd`; image `deepdive:tiering-dfd15d6`. Owner-key protection remains active. Source branch was deployed directly (Option B); main and draft PR remain unmerged. Documentation commits after this record do not change the deployed source revision.

[Machine-readable verification](evaluations/deployment-model-tiering-2026-10-25.json) · [Implementation and routing](model-tiering.md)

## Corrections to supplied deployment suggestion

- Fresh baseline is **21 runs**, not 20 or 14. All twenty-one exact stored run JSON hashes were preserved.
- Host data paths were resolved from the actual deployment. SQLite backup API was used for a consistent backup rather than copying an active WAL database file.
- Actual header is `X-DeepDive-API-Key`, not `X-Owner-Key`. Authentication was checked with **POST** on both paid routes. GET /research normally returns 405 and is not an authentication test.
- `/model-presets` and existing reports remain read-only/public by design. They do not need the owner key.
- Existing gated release helper replaced broad compose down/up. It checks idle state, tests an isolated candidate against copied data, preserves routing/environment, and retains a rollback container. n8n was restarted only after a separate idle-instance check.
- No new environment variables were required relative to e6391af. Existing Mesh, Brave, owner-key and database settings were preserved without printing values. Model choice is stored per new request; configured preset retains MESH_MODEL.

## Backup and packaging gates

Deployment directory: `/docker/deepdive-tiering-dfd15d6`.

- Pre-deployment consistent database: `pre-deploy-backup/deepdive.db`, integrity ok, 21 runs.
- Full evaluation directory: `pre-deploy-backup/evaluation-20261024`, all 24 file hashes verified against original.
- Previous n8n workflow: `pre-deploy-backup/n8n-before.json`, private mode 0600.
- Redacted container listing and private hash/configuration metadata saved on host; secret values were not exported into documentation.
- Final image was built from the dedicated `source/` directory only. Image checks confirmed it does not contain deployment backups, before.json or source.tar. An earlier wider-context build was not promoted; the source-only image is the released image.
- Candidate used a separate consistent database copy. Backend **288 passed, one skipped** (runtime has no Node for optional workflow-JavaScript check). Frontend **34 passed** in image build; Vite/TypeScript build passed. Existing dashboard chunk/deprecation warnings remain disclosed.
- Exact source application CI passed: [backend/frontend workflow](https://github.com/seelamramesh/deepdive/actions/runs/40207696745). Organizer reporting remains separate from application CI and requires a submitted entry; no submission was made.

## Public verification

| Check | Result |
|---|---|
| Container | Running, healthy, restart count 0 at verification |
| Health | status ok, db_ok true, persistent `/app/data/deepdive.db` |
| Stored runs | 21 before / 21 after; every stored JSON hash unchanged |
| Budget/evaluation files | All 24 hashes unchanged |
| Owner key | Same key preserved; root-private file matched container configuration |
| POST research, missing/wrong key | 401 |
| POST follow-up, missing/wrong key | 401 |
| Correct owner key with invalid question | 422 on both routes; validation reached without launching work |
| Model catalog | fast, balanced, quality, configured; default balanced |
| Cost/latency promises | Per-run estimates remain null/not calibrated |
| Legacy report/certificate | Additive verification_disclaimer present; stored text not rewritten |
| Legacy preset | null / Not recorded (historical), not relabeled balanced |
| SPA | Loads; deployed form shows four options and catalog token rates |

All write probes used deliberately invalid question bodies, so no research could be dispatched even if an authorization regression occurred. Keys were not entered in browser screenshots, repository files or output.

Browser checks exercised all four choices without clicking Start. Report disclaimer and historical Audit label were visible. At actual widths 360 and 412 px, form fit the viewport without horizontal overflow and the selector had a 44 px minimum height. Physical Android/notched-device behavior remains untested.

## n8n deployment

Workflow stays active with fourteen nodes. New active version: `3eabb375-454b-4195-9e38-79d2c13bf73a`.

Only Start Research Run gained the model_preset body parameter, using caller value or balanced. Owner-key forwarding, other thirteen nodes and all connections compare equal to the saved definition. Definition/activation was verified through the connector after import/publish/restart. No token-funded n8n research was run; this is not new live model-quality evidence.

## Paid smoke and limits

**Paid smoke skipped. Zero new Mesh inference or Brave requests were made.** Model tiering is deployed and covered by mocked integration tests, but not live-tested for accuracy, speed, per-run price or savings. Catalog metadata presence does not establish structured-output quality. Actual billing remains unknown. Existing evaluation guard is not production-wide spend enforcement.

## Rollback

Rollback was **not needed**. Previous protected e6391af container retained as `deepdive-rollback-ui-20261025161650`. Candidate backup also exists at `validation-data/deepdive.db`. Logs: `promote.log` and `source-only-build.log`.

Before any later rollback, check for new active/completed runs and preserve new data. Prefer reactivating the retained protected container with current persistent data. Do not blindly overwrite the database or ledger from a wildcard backup. If reversing workflow changes, use the saved workflow definition and preserve owner-key forwarding. No old unprotected runtime should be substituted.

Refresh the production page, then open **New research → Model preset**. Submission and application merge remain on hold.
