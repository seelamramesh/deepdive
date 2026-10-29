# DeepDive handoff and pending actions — 2026-10-24

Status: user requested winding up this session. Goal paused, not completed. No hackathon submission. No further paid calls or deployment scheduled by this handoff.

## Exact state

- Repository: https://github.com/seelamramesh/deepdive ; draft PR #1: https://github.com/seelamramesh/deepdive/pull/1 ; branch codex/research-audit-20261024. Main has not been merged by this work.
- Latest independently verified production revision: f6b375f071a3ec6e144a1ca0a754ca9ae6d2effb, image deepdive:scoring-20261024-r1. It contains source-window scoring and per-reference citation-link checks.
- Production does NOT yet contain subsequent contradiction evidence-ID clarification, compact synthesis/changed length retries, report grounding reviewer or its new Audit UI. These are candidate changes on the PR branch.
- Last rollout backup: /docker/deepdive-scoring-20261024-r1/validation-data/deepdive.db (16 runs at backup time). Rollback: deepdive-rollback-ui-20261024164007. SQLite persists at /app/data/deepdive.db. Do not redeploy while any current run is active; recheck live state first.
- Current candidate local validation: 131 backend tests passed (one existing deprecation warning); 23 frontend tests passed; Vite build and TypeScript passed. Dashboard bundle remains 664.05 kB minified / 190.48 kB gzip. Latest candidate has not passed a fresh Linux deployment gate or browser inspection of the new audit section.

## Measured evaluations, with limits

| Evaluation | Measured result | Limit |
|---|---|---|
| SQLite research eval20261024sql01 | END, 17 calls, 52,294 tokens, 154.543 seconds, 8 accepted claims match cited passages | Only one round; 0/5 planned subquestions green, important concurrency limitations omitted |
| K2-18 b research eval20261024exo01 | END with warning, 24 calls, 93,360 tokens, 192.481 seconds, 5/12 accepted | Synthesis hit 4,096-token limit twice; fallback incomplete; journal/preprint are same study |
| Detector baseline | Same-period conflict missed; 2 negative controls passed | Model returned passage text instead of evidence IDs; candidate was correctly rejected |
| Corrected detector replay | 3/3 labelled outcomes matched: 1 conflict, 2 negative controls | Tiny synthetic component test, not real-world precision/recall |
| Compact synthesis replay | Valid JSON, one call, 4,990 total tokens, normal stop | Prose still added details outside accepted atomic claims |
| New report reviewer | 5/5 synthetic line labels matched; saved-report replay withheld 1/7 reviewed units containing unapproved details | One model reviewer; no broad or independent accuracy guarantee; original run unchanged |

Raw evidence and reviews are in this chat's outputs directory. Public factual reviews: docs/live-evaluation-sqlite-2026-10-24.md and docs/live-evaluation-uncertainty-2026-10-24.md. New report-review measurement artifact: DeepDive-Live-Report-Review.json.

## Paid-test budget

User authorized $3 combined Mesh + Brave. Persistent evaluation ledger: /app/data/evaluation-20261024/budget.json. Latest verified conservative reservations: $1.685113; reservation stop $2.50. Remaining reservation capacity: $0.814887. Never reset the ledger to obtain more capacity. Reservations use conservative catalog/public rates and are not verified billed charges. No refunds after failures/unknown usage. The guard is limited to these evaluation processes, not all public application traffic.

## Ordered pending actions

### 1. Verify report review end to end before deployment (highest priority)

- Review candidate report_grounding.py for claim/evidence scope, conflicting or omitted decisions, errors and mixed supported/unsupported clauses. Existing unit tests cover these paths; inspect whether fallback or recovery can still bypass intended audit semantics.
- Run API -> real agents -> final reviewer -> persisted SQLite -> workspace -> browser with labelled unsupported extra clauses, causal/temporal overreach, study attribution, valid paraphrases and factual headings. Keep both positive and negative denominators.
- Confirm report_grounding_audit is returned by the actual workspace endpoint and rendered in the new Final report review section. Retained/withheld units and reasons must be visible; historical missing diagnostics must remain unavailable.
- Verify reviewer failure yields a clearly labelled partial/fallback report, not an apparent fully verified synthesis. All-removed prose may legitimately require a deterministic accepted-claim fallback; document that boundary.
- Add explicit certificate/report limitations for the new model review. Do not describe it as hallucination-free or independent human verification.

### 2. Broaden research completeness and source independence

- Current extraction selects one 7,000-character window from at most 50,000 stored characters. Use targeted gap-round selection to reach missing official passages without silently increasing token/call budgets. Prove later-round windows change where justified.
- Retrieve primary supporting material for omitted subquestions. Source critic now sees selected text, but its heuristic threshold can still discard useful material. Evaluate calibration without simply lowering trust to make output fuller.
- Detect or disclose journal/preprint/mirror relationships. Two URLs are not two independent studies. Avoid spending contradiction calls on duplicate work or counting it as corroboration.
- Classify browser challenge/consent/error pages as retrieval failures or clearly unusable material; do not bypass access controls.
- Preserve full source snapshots, hashes, extraction offsets and rejected candidates. Source dates must not be inferred from missing metadata.

### 3. Complete diverse live evaluation within remaining budget

- Recheck ledger and live process lock first; never restart a marked evaluation solely because an observation timed out.
- Add a multi-round gap-recovery case (current two live research cases used one round), a real contradictory-source question and a temporal/false-premise case. Existing synthetic checks are insufficient proof of real-world contradiction recall.
- Include an n8n -> API -> retrieval -> verification -> report run through the existing 14-node workflow. Current live evaluations invoked deployed agent functions via guarded processes, not browser/n8n.
- Record actual tokens, calls, durations, missing telemetry, expected labels and section-by-section findings. Do not infer actual dollar charges from reservations.
- If remaining budget cannot fund required cases, stop before sending requests and request a new explicit cap; do not silently exceed or reset it.

### 4. UI and mobile verification

- Browser-test new Final report review section with kept/withheld lines, empty historical data, long passages/reasons and source links. Check 360/375/390/412px and desktop for overflow and touch targets.
- Physical Android sidebar, run controls, tabs, keyboard and safe-area verification still needs real-device evidence. Responsive Chromium tests do not prove that requirement.
- Confirm Control Flow clearly separates shared architecture from actual recorded query -> source -> evidence -> verdict events. API session traces are not historical per-run traces.
- Address bundle size if measurement justifies it; do not hide the warning by raising its threshold.

### 5. Usage and cost completeness

- Obtain verified account-specific Mesh/Brave billing details and reconcile observed usage against provider records. Distinguish estimates, reservations and confirmed charges.
- Production-wide per-run budget enforcement and a durable billing ledger are not implemented. Decide/implement them if included in the final feature scope; do not present the evaluation-only guard as product enforcement.
- Historical missing tokens/traces remain unknown. No fabricated backfill. Abrupt crashes can still lose in-flight billing metadata; automatic durable resume is absent.

### 6. Deploy latest candidate safely

- Require fresh Linux backend suite, frontend tests/build/TypeScript and browser checks on exact candidate revision. No claim of release readiness based only on local tests.
- Verify no active/interrupted runs; consistent SQLite backup with integrity/run-ID checks; isolated candidate with copied database; preserve data mount and routing; retain rollback.
- Promote only after gates pass. Independently read runtime image/revision, public health, run IDs, saved reports and new audit payload. Validate rollback if failure occurs.
- Keep current production and candidate revision distinct in docs. Do not rewrite historical research outcomes to appear improved.

### 7. GitHub, rules and final documentation

- Keep latest authorized work pushed to draft PR #1; inspect CI on the exact new revision. Previous green app CI belonged to older revisions, not every later commit.
- Official organizer workflow previously passed 4/4 critical checks but reporting failed because no submission entry exists. Overall organizer run was red and result not recorded. Do not edit official workflow or submit merely to make it green.
- Re-audit attached Agent Arena rules against current implementation: Mesh-only calls including new reviewer, multi-agent behavior, provenance, unsupported-claim handling, gap research, human audit, README/self-evaluation and submission artifacts.
- Once the full goal passes, update complete architecture, Mermaid/visual diagrams, 14-node workflow explanation, deployment, complete feature inventory, examples and jury walkthrough to match actual tested/deployed state. User specifically requested this final update after completion.
- Clearly disclose absent vector database, physical-device evidence, durable resume, cost ledger or other unfinished features. SQLite is not vector retrieval.
- Merge/publish final branch only with appropriate review and scope authorization. Hackathon submission remains on hold until explicit user approval after validation.

## Completion gate

Goal is not complete. Required proof still includes broader live, multi-round and n8n evaluations; final prose verification through the deployed UI; physical Android evidence where claimed; latest candidate rollout/CI; rule-by-rule audit and final jury documentation. Resume from this list, inspect current state before acting, and retain negative results.
