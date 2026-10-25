# Pre-Action 3 offline fixes

All five fixes implemented in agreed order: search observability → retrieval backfill → deterministic report limitations → qualifier feedback → cache telemetry. Source changes use a copied Action 2 fixture, mocked providers and a mocked TTL clock. No paid research or production-data rewrite is needed for these fixes.

## Fix 2 — search observability

`app/services/retrieval.py`, `app/services/orchestrator.py`, Audit UI: success, empty, missing_key, invalid_response, error and timeout are distinct. Attempt ID, timestamp, elapsed duration, HTTP status and safe error class are persisted. Redirect hops share a logical fetch ID with separate request indexes/statuses. No headers, bodies or exception messages enter these traces. Historical absent fields stay unknown. Search attempts appear in retrieval traces and the current search-planning audit.

## Fix 1 — bounded retrieval backfill

`app/core/config.py`, `app/models/schemas.py`, `app/services/orchestrator.py`: successful-source budget stays unchanged. Per-round HTTP fetch attempts are bounded by the smaller of `MAX_FETCH_ATTEMPTS_PER_ROUND` (default 20) and twice the successful-source limit. Failed/duplicate material does not consume a successful-source slot. Untried seeds retain priority; pending search alternatives preserve discovery provenance and carry across rounds. Known same-subquestion alternatives receive priority after a failed search-derived candidate; seeds with unknown owner do not acquire invented ownership. Attempted failed URLs are not automatically retried within the run. Access controls and URL validation remain intact.

## Fix 4 — deterministic limitations

`app/services/orchestrator.py`, schema/API and Audit UI: factual prose still requires approved claim/evidence links. New limitation lines are rendered after strict filtering from derived coverage and saved counts, with separate `report_artifact_audit` records. They are not model-approved facts. A copied Action 2 report retains its five cited/structural units and gains nine deterministic units; the original fourteen deleted model units are not restored. Rendering is idempotent; original fixture checksum remains unchanged.

## Fix 3 — qualifier feedback

`app/agents/runner.py`, `app/agents/prompts.py`: drafter receives the original question plus bounded attributed critiques from current judgments, earlier gap feedback, excluded-claim judgments and prosecutor records. At most eight judge items and twelve combined records are sent; reasons/requirements are truncated to fixed limits. Prompt version changes to `claim-drafter-feedback-v2`. Feedback is explicitly not evidence; qualifiers must be supported by supplied passages or the claim withheld. Tests prove feedback transport, not live semantic success.

## Fix 5 — exact-cache telemetry

`app/core/mesh_gateway.py`, schema/API and Audit UI: lookup reason and storage outcome are separate fields. Reasons include first observed request for an agent in the current run, different exact key, TTL expiry, previous response not stored, capacity-not-stored repeat, disabled scope and ineligible temperature. Storage can report stored, reused, ineligible request/result, disabled, response not stored or capacity not stored. Existing 128-entry cache still does not evict and still uses exact keys only. Metadata is run scoped and bounded to 128 agent histories. Missing historical fields remain null. TTL tests advance a fake clock by 301 seconds; no real five-minute wait.

## Verification checkpoint

- Local backend: 191 passed, one Linux-only lock test skipped; existing Starlette deprecation warning.
- Frontend: 29 passed across four files.
- Production Vite build and TypeScript passed; dashboard chunk 667.17 kB minified remains a known size warning.
- Full backend suite ran after each implementation step. Search/retrieval tests use MockTransport; report/feedback/backfill tests use copied artifacts and mocked IO. The shared real-HTTP transport blocker prevents accidental provider requests in tests.
- Backend API fixture test confirms new outcome fields survive storage/workspace serialization; historical cache telemetry remains null.
- Existing cached/uncached offline end-to-end scenarios remain passing.

## Deployment verification — 2026-10-25 UTC

Runtime `26907d91c87526ee57c61844c96303b59eb6c68b`, image `deepdive:preaction3-26907d9`, is deployed. Documentation commits after this code revision do not change the runtime.

- Exact Linux image: 191 passed, one Node-dependent workflow test skipped. Linux lock test passed; the local suite covers the Node test.
- Image frontend tests: 29 passed; build and TypeScript passed. Known jsdom chart dimension warnings and chunk-size warning remain; these are not physical-device evidence.
- Staged against consistent copied SQLite database, with no public routing. Synthetic outcome/cache examples existed only in a clearly labeled copied-data replay.
- Candidate Report/Audit checks requested 360, 375, 390, 412 and 1440 px; no page overflow. Public Audit also checked actual 360, 375, 390, 413 and 1440 px (412 requested rendered as 413 in browser emulation), with no page overflow. Physical Android remains unverified.
- Browser verified safe HTTP outcome display, cache decision/storage status and deterministic limitations. Public historical fields remain unknown; old reports are not regenerated.
- Fresh pre-promotion active-run check and consistent backup verified 19 records. Backup: `/docker/deepdive-preaction3-26907d9/validation-data/deepdive.db`.
- Previous image starts against an independent copied database and serves health/run records without AI keys; automated rollback failure-path test remains passing. No forced live rollback drill was performed.
- Independent post-promotion verification confirms public health/DB readiness, SQLite integrity `ok`, no active runs, no synthetic fixture in production and all 19 stored JSON records unchanged against backup.
- Rollback container: `deepdive-rollback-ui-20261025042544`, preserving previous `30312f9` runtime and persistent data mount.
- Entire evaluation ledger equals the Action 2 ledger, including all prior entries and authorization history: $2.840527 reserved, $3.50 stop, $0.659473 remaining reservation capacity, $4 authorized. Actual provider billing unknown.
- [Backend/frontend CI for exact runtime passed](https://github.com/seelamramesh/deepdive/actions/runs/40161590583). [Organizer job](https://github.com/seelamramesh/deepdive/actions/runs/40161586745) passed 4/4 critical checks, then failed reporting with 403 because no hackathon submission exists. No submission made to clear CI.

 No live quality improvement or savings is claimed. Remaining reservation capacity at the prior measured checkpoint is $0.659473; it is not confirmed provider balance. Action 3 requires its separate approval and a fresh guarded-budget preflight.
