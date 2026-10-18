# Prompt Reference Review

References reviewed:

- [Samarth0211 prompt-shortcut gist](https://gist.github.com/Samarth0211/2fd03ca00c56001315e64ef8bd54c65a)
- [ChatGPT Secret Codes PDF](https://mavgpt.ai/pdfs/ChatGPT_Secret_Codes.pdf)

## Finding

These materials describe prompt aliases and reasoning mnemonics, not hidden model capabilities, verified APIs, or security controls. Strings such as `OODA`, `FACTCHECK`, `REDTEAM`, `HIDDENASSUMPTIONS`, and `BLINDSPOTS` do not guarantee factuality merely by appearing in a prompt.

## What DeepDive Reused

| Pattern | Concrete implementation |
|---|---|
| OODA | Persisted state machine: plan, search, retrieve, verify, measure coverage, research gaps, synthesize. |
| FACTCHECK | Atomic claims must reference stored evidence; Judge validates evidence IDs before accepting support. |
| REDTEAM / devil's advocate | Prosecutor challenges claims, Defense argues support, Judge issues verdict. |
| HIDDENASSUMPTIONS / BLINDSPOTS | Coverage map exposes thin sections; red/yellow areas trigger another bounded research round. |

## What DeepDive Did Not Reuse

- No “secret code” is treated as a privileged command.
- No prompt phrase substitutes for schema validation, exact-passage checks, source scoring, audit logs, or tests.
- No reference claim is accepted as evidence for hackathon compliance.
- No autonomous swarm was added merely for agent count; specialized agents remain bounded and role-specific.

## Practical Rule

Prompts state contracts. Code validates contracts. Persisted artifacts and measured evaluations prove behavior.
