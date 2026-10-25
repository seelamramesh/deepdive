# Research API access and endpoint redaction

Paid mutation routes `POST /research` and `POST /runs/{id}/follow-up` require `X-DeepDive-API-Key`. Configure a separate random `DEEPDIVE_API_KEY` (at least 32 bytes); never reuse Mesh, Brave or submission credentials. Missing/short server key locks research with 503. Missing/wrong caller key returns 401 before saving or scheduling a run. Query-string/body keys do not authenticate. Comparison is constant-time.

The React research form asks for the key in a password field. It sends it only as an HTTP header to the configured backend, not in the question/body, AI input, persisted run, or browser local/session storage. Browser process memory still contains the entered key while the client handles it. Only enter it on the trusted HTTPS deployment; do not put it in frontend environment variables or bundled code. Read-only reports, run lists and evidence remain public. This protects paid actions; it is not per-user authentication, a global spend cap or DoS protection. Rotate the key if disclosed.

The fourteen-node n8n workflow forwards the caller's `x-deepdive-api-key` from Webhook to Start Research Run. It must never attach a private server key automatically for anonymous webhook callers. n8n execution records can contain inbound headers; keep n8n administrative access and execution exports private. The backend enforces authentication even if the public workflow has not yet been upgraded.

## Deployment

Generate a 32-byte-or-larger random key on the deployment host, store it in a root-only file, and pass `--api-key-file /private/path/to/key` to `scripts/deploy_ui.py`. Its temporary environment file is mode 0600 and removed after deployment. The key is not a command-line argument, log output, GitHub secret or repository file. Subsequent releases preserve the configured container environment. For compose/local deployment, add `DEEPDIVE_API_KEY` to the gitignored `.env`.

Public readiness hostname now comes from `--base-url` or `DEEPDIVE_BASE_URL`. Legacy routing script requires `DEEPDIVE_PUBLIC_HOST`. Evaluation controllers and usage-report script use `DEEPDIVE_BASE_URL`, with loopback fallback. Example evaluation report links use the deliberately non-resolving `deepdive.example.invalid` placeholder; append the recorded run ID to your private deployment URL to inspect a run.

Do not send keys in a URL, command pasted into a public issue, screenshots or exported workflow JSON. API clients and n8n callers must attach the owner key as a header. Historic evaluation launch scripts also require the new header before they can start research; do not treat them as an auth bypass or run them without renewed test budget authorization.

## Scope of repository cleanup

Live endpoint appeared in twelve tracked files, including scripts and fixture documentation, rather than one evaluation document. References are replaced with configuration or redacted examples on the current branch. No history rewrite is performed. Previous commits, cached pages, DNS and certificate transparency may still reveal the hostname; concealment is not access control. The default branch must be reviewed separately before claiming every branch is redacted.

## Verification protocol

- Offline tests check disabled/missing/wrong/correct keys, both mutation routes, no scheduling on denial, public reads, key exclusion from saved runs/agent arguments and n8n caller-header forwarding.
- UI tests check password input, header transport, absence from request JSON and no local/session storage.
- Candidate and production probes use invalid research bodies: rejection cannot create a paid run even if auth is broken.
- Preserve all stored research runs and budget ledger; do not launch live inference to test access control.
