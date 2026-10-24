# Pre-submission deployment verification — 2026-10-24

Deployed runtime: 03e239a8ea387b0e799073b10c9f83a7964079fd, image deepdive:prejury-03e239a. Public health, database readiness and Docker image/revision independently rechecked after promotion. This deployment does not establish hackathon readiness.

## Exact-revision gates

- Docker frontend build and TypeScript passed; 25 frontend tests passed. Existing bundle and jsdom chart-dimension warnings remain.
- Python Linux candidate: 150 tests passed, 1 skipped, 1 existing deprecation warning (5.31 seconds at initial staging; 3.02 seconds at promotion validation). Skipped test requires Node to evaluate n8n expressions; backend Python runtime has no Node. Same test passed locally where Node is installed. No claim of 151 Linux passes.
- Application CI backend and frontend passed on 03e239a: https://github.com/seelamramesh/deepdive/actions/runs/40118736784 . Organizer check remains red; no submission performed.
- Consistent SQLite backup integrity passed, 18 original saved runs. No active runs at preflight and promotion recheck. Temporary candidate used a copied database, plus one copied real prior evaluation row for report-audit UI inspection. This extra row was not added to production.
- Browser candidate: audit at five widths plus all seven views at mobile/desktop = 19 no-overflow checks. Responsive Chromium, not physical Android verification.
- Candidate API preserved all 18 production IDs; selected historical reports unchanged. Public after rollout: 18 saved runs and the user report c324ed4de85d4e3c unchanged. Historical review status correctly not_available rather than invented decisions.
- n8n container reached the newly deployed backend through its existing configured URL; GET /health returned status ok and db_ok true. This was a connectivity check, not a new research execution.
- Public Audit UI rendered historical missing-review disclosure; mobile check had no page overflow.

## Backup and rollback

Backup: /docker/deepdive-prejury-03e239a/validation-data/deepdive.db
Rollback container: deepdive-rollback-ui-20261024180835
Release directory: /docker/deepdive-prejury-03e239a
Persistent production database remains /app/data/deepdive.db with existing bind mount.

Temporary candidate and localhost browser tunnel were stopped after inspection. Production promotion used the existing backup/check/automatic-rollback script. Rollback retained; no forced rollback drill performed on the live application.

## New behavior now deployed

Report model review, kept/withheld audit and final-inclusion distinction; explicit partial/fallback labels and model-review limitations; compact synthesis and changed requests on truncated retries; contradiction evidence-ID instructions; gap-targeted bounded extraction; duplicate material handling; unusable-page audit; recorded publication-date uncertainty; source-critic selected-window context. These apply to new runs. Existing saved reports and their historical certificates were not regenerated.

## Paid rerun gate

No new Mesh/Brave requests started during deployment. Persistent evaluation reservations remain at the last verified $2.138282, with $0.361718 before the conservative $2.50 stop under the user's $3 ceiling. A fresh full n8n research run with primary sources is pending an explicit increase in the cumulative cap or an adequately bounded affordable evaluation. Budget-increase question is pending; silence is not approval. Never reset existing reservations or call costs confirmed invoices.

Still pending: fresh n8n research on this deployed revision, broader source/claim review, sufficiently complete coverage, remaining adversarial/temporal/real-contradiction evaluations and final jury documentation after the goal completion gate. Hackathon submission remains on hold.
