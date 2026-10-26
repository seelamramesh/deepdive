# Research admission and concurrency

One process-global asyncio semaphore limits complete research pipelines, including direct orchestrator calls. Both research creation and follow-up authenticate before reserving capacity. Reservations are made before saving or scheduling, preventing a burst from overbooking slots before background tasks start.

| Environment setting | Default | Meaning |
| --- | --- | --- |
| `DEEPDIVE_MAX_CONCURRENT_RUNS` | `3` | Validated range 1–20 |
| `DEEPDIVE_REJECT_WHEN_FULL` | `false` | Queue if false; reject excess admission with HTTP 429 if true |

Restart after changing settings. Production deployment selects `3` and `true` to avoid an unbounded queue; the application default remains false for compatibility.

`GET /health/concurrency` and its alias `GET /api/health/concurrency` return:

```json
{"max_concurrent":3,"active_runs":0,"queued":0}
```

`queued` includes accepted reservations awaiting execution, including the brief persistence/scheduling interval. Accepted responses retain `status: started`; no per-run queue status is added. Existing write endpoints are `/research` and `/runs/{run_id}/follow-up`, without an `/api` prefix.

Rejected requests return a top-level JSON object and create no saved run:

```json
{"error":"server_busy","message":"Maximum concurrent research runs reached. Try again later.","max_concurrent":3}
```

The API context manager and orchestrator share one admission only within the same task. Child tasks must acquire independently. Counter mutations have no await and are atomic on the single application event loop. Cleanup covers success, exceptions, queued/active cancellation, cancellation before task entry, save failure and scheduling failure. The completion callback is necessary for cancellation before coroutine entry; release is idempotent.

## Verification and limits

`tests/test_concurrency.py` adds 17 offline cases. Local full backend result before deployment: **305 passed, 1 skipped**, with the existing Starlette deprecation warning. Tests use mocked pipelines and in-process HTTP, with external HTTP blocked. No paid concurrency load test was performed.

This is a per-process execution cap, not a distributed or durable queue, spending cap, request rate limiter, or fairness guarantee. Multiple workers each receive their own cap. Queue mode is unbounded and pending tasks do not survive restart. The deployment uses the existing single Uvicorn process. Model presets, Mesh calls, agent runners, prompts and frontend are unchanged.
