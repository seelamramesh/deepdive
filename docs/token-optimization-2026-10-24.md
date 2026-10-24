# Token optimization and authorized $4 test budget — 2026-10-24

User explicitly raised cumulative Mesh + Brave testing ceiling to $4 (not $5). Existing ledger was preserved. Reservation stop increased from $2.50 to $3.50 with a timestamped authorization entry and pre-change backup. Existing reservations remain $2.138282; remaining reservation capacity $1.361718. Actual billed dollars remain unverified. No paid research started in this change.

## Critical reading of supplied guidance

Reference: https://www.firecrawl.dev/blog/llm-token-optimization . Useful sequence: measure task usage; reduce unnecessary retrieved/repeated context; keep stable prompt prefixes; cache; limit unnecessary output; evaluate quality before routing/compression changes. Vendor benchmarks and worked monthly savings are not DeepDive results. Answer-format extraction is lossy and may introduce additional AI calls; do not adopt a third-party AI extraction route without verifying Mesh-only compliance.

Mesh also describes an account-private temporary exact-response cache, entries expiring within 24 hours, configurable by key/request: https://meshapi.ai/ . This is not proof it is enabled on this key or that recorded repeated responses were billed at zero. Local cache, gateway response cache and provider prefix/KV cache are separate mechanisms. No provider-specific cache_control, batching API or alternate model endpoint was enabled without compatibility evidence.

## Candidate implementation

- Exact structured-response cache, private to one research run and cleared in finally on completion/cancellation/recovery. Entries expire after five minutes; at most 128 entries. No disk or cross-run answer cache, no semantic similarity cache.
- SHA-256 key includes official endpoint, agent, prompt version, full messages, model, temperature, response format and output limit. Changed evidence/source hashes included in payloads invalidate matching. Nonzero temperature disables local caching.
- Only successful parsed responses with an expected non-empty result field are eligible. This basic shape check is not full semantic verification; the ordinary agent validators, claim judge and report reviewer still run downstream. Failed requests/malformed JSON are not reused. New source/evidence context is not skipped to save tokens.
- Deep copies prevent a caller's mutations from altering cached responses. New run/concurrent run scopes are isolated. MESH_RUN_CACHE=false disables this optimization for A/B diagnostics.
- Cache audit records cache_hit, request_sent=false, source call ID and usage_source=local_cache_incremental. Token fields zero on these events mean zero incremental API tokens sent by this application, not a provider-reported usage record. Original provider tokens are counted once, not copied onto the reuse event.
- Actual requests record request_sent=true. Provider cached input tokens and request IDs are captured only when returned; missing values remain unknown. No dollar discount is inferred from cached token counts.
- UI distinguishes cached events; usage export separates local reuse from confirmed sent requests. Historical request_sent remains unknown, not fabricated as true.
- Existing immutable source reuse, bounded gap windows, duplicate-material detector skip, compact synthesis and altered truncated retries continue. All actual inference remains Mesh-only.

## Validation

167 backend tests passed, one existing deprecation warning, 4.47 seconds. Includes seven pipeline scenarios with cache disabled and enabled (14 mocked-I/O integrations), exact repeated request/copy protection, version/evidence/model/format/output-limit changes, concurrent run isolation, malformed response misses, five-minute expiry, provider metadata uncertainty, budget-cap history and no token double counting. One repeated-request unit test proves two identical logical calls produce one provider invocation; this is not a measured whole-application savings percentage.

26 frontend tests passed; Vite build and TypeScript passed. Existing large-bundle warning remains. No new Linux candidate/browser release gate or live cache quality/cost measurement yet. Production remains runtime 03e239a until a separately validated rollout; these optimizations are candidate code only.

## Next optimization/evaluation steps

1. Deploy exact-cache candidate only after Linux/frontend/browser gates, preserving 18 saved runs and rollback.
2. Run one bounded real research case with primary sources through n8n under a verified shared reservation guard. Ordinary production n8n calls are not automatically governed by the evaluation-only ledger; do not launch an unguarded request and call it capped.
3. Compare logical calls, actual sent requests, local reuse, provider-reported cached input, total input/output and latency, alongside claim/section quality. Reconcile billing with provider records when available.
4. Reduce repeated payloads while preserving original passages, dates, conditions and provenance. Do not use a summary as a replacement for verification evidence.
5. Evaluate per-agent output limits and batching with positive/negative controls before changing defaults. Provider batch discounts and prefix-cache discounts require Mesh/account confirmation.

The $4 limit is cumulative, not a fresh $4 allowance. Never reset reservations. Submission remains on hold; no claimed 40–80% savings or hallucination-free caching.
