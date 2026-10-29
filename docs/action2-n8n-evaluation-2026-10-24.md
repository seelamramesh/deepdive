# Action 2: guarded n8n evaluation preparation (historical checkpoint)

## Status

Historical preparation checkpoint — now superseded by [completed measured results](action2-n8n-results-2026-10-24.md). Explicit confirmation subsequently received; one guarded run completed and normal service restored.

At the preparation checkpoint: prepared; **not launched**. Automatic approval review rejected the launch because it requires explicit confirmation after the Action 1 gate for paid execution and a temporary production entry-point change. No workaround or alternate launch was attempted. Confirmation is pending.

Read-only verification after rejection: production remains `deepdive:cache-30312f9`, normal uvicorn entry point; controller marker/log absent; admission marker absent; budget unchanged at 66 reservations totaling $2.138282. No new research or cache measurements exist.

## Concrete run plan

Question: How do FDA and USDA divide federal oversight of cell-cultivated chicken for human food in the United States, and what does FDA pre-market consultation establish versus not establish?

Path: existing production n8n webhook `/webhook/deepdive-research` â†’ production backend â†’ official Mesh. Active workflow `vXuzyMGtoaIr2Gcu`, version `9e0edda7-3082-4f5a-97d5-e7265edde36e`, 14 nodes. n8n backend URL independently verified as the production DeepDive URL. No workflow mutation is needed.

Primary starting URLs:
- https://www.fda.gov/food/food-ingredients-packaging/human-food-made-cultured-animal-cells
- https://www.fsis.usda.gov/policy/fsis-directives/7800.1

Limits: maximum two rounds, two active claims, two sources per round, one search query per round, one contradiction batch, 4096 output tokens and two JSON attempts. Cache remains enabled; no extra repeated inference will be inserted to manufacture hits. These restricted settings must accompany any quality interpretation.

Planning allowance $0.80 is an estimate, not measured spend or an upfront charge. Per-run reservation ceiling $1.10; global conservative stop $3.50; authorized total $4. Current remaining reservation capacity $1.361718. Actual billing unknown.

## Guard

`scripts/action2_n8n_server.py` is a temporary, read-only mounted entry-point wrapper around the same backend image. A Linux exclusive process lock spans its lifetime. All mutations except one exact matching research request are rejected. Durable admission marker prevents duplicate launch even after observation loss. Each actual Mesh transport attempt and Brave search is conservatively reserved before invoking the transport; cache reuse bypasses inference and therefore requires no additional reservation. Old ledger entries and authorization history remain intact. Failed attempts retain reservations.

`scripts/run_action2_n8n_host.py` backs up SQLite, verifies idle runs, temporarily stops the normal backend, starts the guarded entry point with existing routing/data/secrets, checks the lock and rejection behavior, dispatches the n8n webhook once with no retry, records progress/response, and restores the original entry point after terminal state. It does not stop a still-active run on an observation deadline. Credentials are copied in memory to a temporary mode-0600 file, never logged, and removed afterward.

Host release directory: `/docker/deepdive-action2-20261024`. No controller process started. Do not relaunch if a controller/admission marker later exists; inspect authoritative state instead.

## Tests and limits

- Local backend suite: 174 passed, one Linux-only lock test skipped.
- Exact production image plus read-only guard/test overlays, isolated without credentials: 13 guard/budget tests passed on Linux, including lock contention.
- Tests verify body preservation, duplicate and wrong-configuration rejection, persisted reservation before transport, old-history preservation, dispatch blocking, and retained reservations after timeout.
- Host controller syntax checked; actual production switch/restoration is not yet exercised for this evaluation. Existing deployment rollback tests are separate evidence.
- Official Mesh models catalog was read without inference. Current selected model rates match the guard assumptions: normal $0.10/$0.50 and long-context $0.50/$2.50 per million input/output tokens. Guard uses twice the long-context rates, UTF-8 byte allowance plus overhead, and maximum output. Reservations are conservative accounting, not invoice-level enforcement.
- SDK `models.list()` cannot parse the catalog's list response; raw authenticated JSON retrieval succeeded. No inference was needed for that check.

## Measurement discipline

After the one run, report cache hits, actual dispatch attempts, response/usage coverage, prompt/completion tokens, call latency, webhook wall time, report review, source/claim/coverage outcomes, and reservation delta. Missing expiry/different-key telemetry stays unavailable. Cached output hashes may be compared to origin calls; this is not an independent cached-versus-uncached quality experiment. Do not estimate saved tokens or latency by multiplying hits by an average. Provider discounts and actual billed charges remain unknown without provider billing evidence.

Action 3 and hackathon submission remain on hold.
