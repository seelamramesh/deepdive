# Action 2 and supplied n8n workflow review — 2026-10-24

Scope: Action 2 authorized; supplied workflow inspected alongside it. Candidate-only changes. No Mesh/Brave calls started by this action, no workflow import/activation, no production deployment or submission.

## Implemented changes

- Gap-round extraction uses weak subquestions and completion criteria, with previously analyzed offsets, instead of repeating only the original question. Lexical relevance ranks first; previously uncovered characters break ties. One contiguous window of at most 7,000 characters per source remains; this heuristic may still select overlapping windows or miss synonyms.
- Retrieval audit records selection query, old/new window offsets, snapshot/slice hashes and fetch outcomes. Existing sanitized source snapshots remain immutable; historical content is not reconstructed.
- Sources retain explicit DOI metadata and validated publication dates when available. Missing dates remain null; critic recency becomes unknown without a recorded publication date. Source critic limitations now persist.
- Source material grouping uses shared DOI identifiers, matching snapshot hashes and a limited probable-match rule for identical long publication titles across arXiv and IOPscience. The title rule is heuristic, not verified identity. Unknown/distinct groups do not prove independence. Existing source records are retained; grouping is exposed separately in workspace output.
- Source critic cannot label matching material as independent/corroborated; its original reported flags are retained separately for audit.
- Duplicate material cannot satisfy the green multi-source gate. Coverage exposes distinct_material_count alongside URL-based source_count. Detector avoids paid comparisons within a material group, records skipped_same_material and explains it in UI. Certificates disclose these counting limits.
- Browser challenge, consent, empty/error content and transport/unsafe/unsupported retrieval failures now have structured audit outcomes; unusable pages are excluded from source creation. This is a heuristic classifier, not perfect page understanding; access controls are not bypassed.

Prompt versions: source-critic-provenance-v3 and contradiction-material-groups-v4. Extraction policy: gap_lexical_window_v2.

## Tests and evidence

Fresh backend: 151 passed, one existing Starlette/httpx warning, 3.48 seconds. Frontend: 25 passed; Vite build and TypeScript passed. Existing 665.18 kB / 190.74 kB gzip dashboard warning remains.

The existing two-round API -> agents -> orchestrator -> SQLite fixture was strengthened: round 1 selected the opening; round 2 used the missing-area query and selected a different later window, with unchanged 7,000-character budget and correct hashes/offsets. Provider/search/fetch I/O is mocked in this fixture; it is not a paid live gap-recovery measurement.

Additional regressions cover DOI grouping, observed journal/preprint titles, no green duplicate corroboration, no paid detector call for one material group, challenge rejection, legitimate reCAPTCHA tutorial retention, validated metadata dates, unknown date normalization, preserved snapshot/hash/metadata, workspace grouping and non-string workflow questions. Live page probes performed only ordinary public HTTP retrieval; no paid APIs.

## Source critic threshold evidence

See evaluations/source-threshold-audit-2026-10-24.json. Four manually topically relevant records from two prior live questions: 1/4 excluded at threshold 0.4; 0/3 primary-material records excluded. Journal/preprint records concern the same study. The excluded secondary record contained relevant single-writer evidence, but relevance alone does not establish authority. No irrelevant-source negatives or authority-labelled gold set exist in this sample; scoring precision, true false-rejection rate and an optimal cutoff remain unproven. Threshold unchanged at 0.4.

## Real journal/preprint probe

The IOPscience URL currently returned a Radware Bot Manager Captcha. The arXiv page exposed the expected title but no journal DOI metadata in the inspected fields. Therefore DOI-only grouping cannot be claimed to handle this observed pair. The exact known title pair is tested under the explicitly probable journal/preprint-title rule. The CAPTCHA title is now rejected by the classifier. Metadata assertions can be incorrect; title grouping can over-group coincidentally identical titles, so it must not be described as bibliographic certainty.

## Supplied workflow

Input: H:/Downloads/DeepDive - Self-Verifying Research (1).json. 14 nodes; connection graph matches repository workflow. Research/verification run in the backend; workflow itself contains no direct inference node/call.

Two issues:

1. Validation called trim() without checking the question's type. Numeric/object/array inputs could throw in n8n rather than take the invalid-input branch. Candidate expressions guard body/question type first. Node-based tests execute these expressions against missing, non-string, short and valid inputs.
2. Supplied Wait parameters are empty. Current upstream n8n source defaults amount to 1 and unit to hours; actual installed-version defaults were not inspected. Corrected export explicitly uses amount=5, unit=seconds, matching repository intent. This avoids relying on defaults and does not claim a measured one-hour delay on the deployed instance.

Primary reference: https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/Wait/Wait.node.ts

Corrected supplied export: outputs/DeepDive-Workflow-Validated-Candidate.json in this chat's workspace. Original attachment unchanged; no import or activation performed. Repository n8n/deepdive-research.json received only the three validation-expression corrections; it already specified five seconds. End-to-end execution in the user's installed n8n remains pending under Action 3.

## Remaining boundaries

Action 2 code paths have offline/persisted-artifact evidence, not a new live multi-round quality score. Broader trust calibration, bibliographic identifier enrichment, perfect challenge detection and general semantic retrieval remain unproven. Group-based skipping can miss disagreements between different versions of one publication. New frontend explanation has component tests/build but no fresh browser check this action. Deployment still requires exact-revision Linux/browser/backup gates. Latest paid ledger observation remains $2.138282 reserved against a $2.50 reservation stop; this action did not reset or charge it. Actual billed dollars remain unknown.
