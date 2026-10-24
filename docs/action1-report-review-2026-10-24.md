# Action 1: report grounding review — 2026-10-24

Scope: user asked to follow deepdive-gaps-prompt.md. Its final instruction restricts work to Action 1 until human confirmation for Action 2. No production deployment or hackathon submission performed in this action.

## Code review findings and corrections

1. All-withheld or citation-invalid generated prose fell back without distinguishing report-review failure from unavailable synthesis. Fallback now records report_grounding_status=accepted_claim_fallback, a factual report_fallback_reason, a warning and a deterministic accepted-claim report. Fallback copies previously accepted claims; it is not a successful generative prose review.
2. Model-kept units could be removed by later citation filtering while Audit still implied they appeared in the final report. Each recorded decision now additionally exposes included_in_final_report. Original kept decision is preserved rather than rewritten. UI shows both stages.
3. Model-review limitations were missing from certificates and report UI. Both now explicitly state review is not a hallucination-free guarantee or independent human verification. Historical missing audits retain not_available; no backfill.
4. Existing strict checks for missing/duplicate decisions, boolean approvals, unknown evidence and mixed-unit rejection remain. Normal and recovery orchestration paths invoke review before citation validation. Unit tests cover reviewer exception, empty decisions, labelled fallback, invalid citations after model approval and workspace exposure.

## Fresh local validation

- 134 backend tests passed, one existing Starlette/httpx deprecation warning, 3.23 seconds.
- 24 frontend tests passed; Vite production build and TypeScript passed. Dashboard bundle 664.99 kB / 190.67 kB gzip; warning retained.
- These local checks are not a fresh Linux release-candidate gate. No deployment claim is made.

## Real HTTP integration (candidate c55ae26)

Isolated candidate process used real HTTP POST /research, real Mesh agents, real source fetch/Brave retrieval, report verifier, separate persisted SQLite database and real GET workspace endpoints. Candidate SPA assets were served by the same FastAPI app through a temporary localhost-only SSH tunnel. No provider/search/agent functions were mocked.

Question: In SQLite WAL mode, can multiple writers write simultaneously?

Run c2563294293842b9: END, one round, two source records, eight passages, two active/accepted claims, 12 successful recorded Mesh calls, 38,987 tokens, no missing usage values, 76.873 seconds to final checkpoint. Test-only bounds: max_claims=2, max_sources_per_round=2, max_search_queries_per_round=1. This is not a test of default maximum-scale behavior or multi-round gap recovery.

Ten report units reviewed: nine model-kept and one withheld. Six model-kept units were included after citation filtering; three model-kept units were later removed. Status reviewed_partial. Raw audit, certificate limitations and final report were returned by the workspace endpoint, persisted in a separate candidate SQLite database and observed in browser. The answer explicitly remains incomplete; selected evidence did not establish writer-writer behavior. Do not treat 2/2 internal acceptance as complete question coverage.

Candidate database: /app/data/evaluation-20261024/action1-candidate.db. Production database was not replaced. Candidate blocks further POST calls with HTTP 405 after the one research request. Candidate server, temporary tunnel and temporary browser tab were stopped after checks.

## Browser evidence

Audit rendered kept/withheld text, reviewer reasons, final-inclusion status and model limitations. Tested widths 360, 375, 390, requested 412 (browser reported 413) and 1280 pixels: five no-page-overflow checks. Expanded withheld-unit reason inspected. Screenshot: DeepDive-Action1-Mobile-Audit.png; measurements: DeepDive-Action1-Browser-Checks.json. These are responsive browser checks, not physical Android evidence. Historical-empty and fallback states additionally have frontend regression coverage; they were not separately replayed in this real HTTP run.

## Real-Mesh labelled component review

Seven fictional units, no new retrieval or full pipeline per unit. Two accepted claims and their original passages supplied. One successful Mesh call, 1,661 tokens.

| Case | Expected | Actual |
|---|---|---|
| Extra clause present only in source, not accepted claim | Withhold | Withheld |
| Causal overreach from observational association | Withhold | Withheld |
| Temporal overreach from FY2025 to every year | Withhold | Withheld |
| Attribution expansion from one study to all studies | Withhold | Withheld |
| Valid synonymous paraphrase | Keep | Kept |
| Supported factual heading | Keep | Kept |
| Unsupported causal factual heading | Withhold | Withheld |

Observed denominators: 5/5 labelled unsupported units withheld; 2/2 labelled supported units retained. Small synthetic component set, not independent or broad model accuracy evidence. These seven are not seven complete API-to-browser runs. API-level adversarial fault injection across all types remains unproven by this action.

## Budget and deployment boundary

Same persistent ledger, never reset: /app/data/evaluation-20261024/budget.json. Latest combined conservative reservations $2.138282; stop $2.50; remaining reservation capacity $0.361718. User ceiling $3. Actual billed costs remain unverified. No further paid work scheduled here.

Production independently rechecked: deepdive:scoring-20261024-r1, revision f6b375f071a3ec6e144a1ca0a754ca9ae6d2effb. Action 1 changes remain candidate-only on draft PR #1. Subsequent release requires Action 6's exact-revision Linux/frontend/browser gates and backup/rollback checks. Official workflow remains untouched.

## Action 1 acceptance limits

Code review, focused corrections, workspace exposure, real API integration, visible real review audit, model limitation disclosures and local regressions have evidence. Reviewer failure/all-withheld behavior is demonstrated with deterministic regressions, not a paid full-pipeline failure run. Five requested case types have real reviewer-component labels; full API-to-browser adversarial coverage for every case is still pending. No claim of complete Action 1 acceptance, full goal completion, production rollout or hackathon readiness.

Wait for human confirmation before Action 2, as the supplied prompt requests. Final architecture/jury documentation remains gated on the full goal completion audit.
