# Concurrency production deployment — 25 October 2026 (America/Chicago)

Deployed application revision **`6dff95f5102e5fc5b81c86638084b40db4503a8d`**, image `deepdive:concurrency-6dff95f`, directly from the existing feature branch. Main and draft PR remain unmerged. No hackathon submission was made. Later documentation commits do not change the deployed application revision.

[Implementation](concurrency.md) · [Machine-readable verification](evaluations/deployment-concurrency-2026-10-25.json) · [Exact-source CI](https://github.com/seelamramesh/deepdive/actions/runs/40265840038)

## Configuration and gates

- Production explicitly selects `DEEPDIVE_MAX_CONCURRENT_RUNS=3` and `DEEPDIVE_REJECT_WHEN_FULL=true`; application default remains queue mode (`false`). Only these two non-secret settings were changed. Provider settings and owner key were preserved without printing them.
- Existing single-process Uvicorn command and effective worker configuration were checked. This cap is not shared across multiple processes or containers.
- Fresh local backend: **305 passed, 1 skipped**. Isolated production-image candidate: **305 passed, 1 skipped**, 4.47 seconds. Existing Starlette deprecation warning remains. The image has no Node for the optional workflow-JavaScript check.
- Image build: frontend **34 passed**, four test files; TypeScript/Vite build passed. Existing large-dashboard-chunk warning remains.
- GitHub application CI for the exact source commit completed successfully. This does not establish hackathon submission or organizer acceptance.
- A consistent SQLite backup was made through the SQLite backup API. Candidate testing used a separate data copy. Promotion was withheld unless stored runs were terminal and unchanged since backup.
- The established promotion helper was copied into the private release directory with only deployment-specific environment overrides and explicit concurrency readiness gates. Public readiness failure would restore the prior container. The repository's general helper was not changed.

## Verified after promotion

| Check | Observed result |
| --- | --- |
| Container | Running, Docker healthy, deployed revision matches |
| Database | `db_ok: true`, persistent bind mount |
| `/health/concurrency` | `{"max_concurrent":3,"active_runs":0,"queued":0}` |
| `/api/health/concurrency` | Same result |
| Rejection configuration | Enabled in runtime and deployment environment file |
| Saved research artifacts | All 21 exact stored JSON hashes preserved |
| Evaluation files | All 24 hashes preserved |
| Both write routes, absent/wrong key | 401 |
| Both write routes, owner key plus invalid question | 422; no work launched |
| New paid Mesh/Brave calls | Zero |

Tests exercise 429 and queued execution with mocked pipelines. No live paid saturation/load test was performed. Health counts were zero at verification; this is deployment evidence, not a measured production capacity benchmark. Accepted API responses retain `status: started`, including queued requests if queue mode is selected.

## Rollback

Rollback was not needed. The prior protected image/container is retained as `deepdive-rollback-ui-20261026035036` (host timestamp in its generated name). Consistent data backups and release logs are retained under the private host release directory. Before any rollback, check active work and preserve new database/evaluation data. Do not overwrite current data with an old backup or restore an unprotected historical container.

No MeshGateway, agent runner, prompt or frontend code changed. This limiter is not a spending cap, global request rate limit, distributed queue or crash-safe resume mechanism.
