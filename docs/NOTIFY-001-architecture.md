# NOTIFY-001 architecture

`notification_gateway/` is a standard-library-only server-side package. A
strict event schema and producer allowlist feed a transactional SQLite
event/outbox store. The worker claims a fenced lease, persists a send intent,
and sends through Direct Telegram only. A provider receipt is persisted and
verified against message ID, configured chat ID, and the exact text digest
before delivery is marked verified. Ambiguous transport outcomes become
`UNKNOWN` and are not resent.

The gateway is deliberately separate from the static Dashboard frontend.
There are no browser secrets, arbitrary destinations, arbitrary URLs, live
Telegram tests, Actions artifacts used as state, or automatic fallback after
an ambiguous send. The CLI provides presence-only doctor, persistent queue
health, and one-worker processing commands.

The package supports the repository's assurance vocabulary by carrying exact
repository, head SHA, PR, issue, and run provenance as evidence. Evidence is
descriptive and does not grant authority. Local producer adapters authenticate
at the gateway boundary, while the dry-run adapter never performs network
side effects. Existing Dashboard checks and the evidence/Claude workstreams
remain unchanged.

Event identity is scoped by `producer/repo/business_id/event_id`; incident
versions use a per-scope sequence and supersede only older pending work.
GitHub run references accept positive 64-bit-safe integers. Expired leases are
fenced before intent, receipt, or pause transitions. Operator reconciliation is
recorded as `OPERATOR_ATTESTED`, never as a provider receipt.

## Dual report delivery

`ReportStore` extends the same SQLite state with canonical report retention,
revision/content hashes, previous-report links, required structured sections,
and independently keyed ChatGPT and Telegram deliveries. Telegram uses
deterministic section-bound chunks; ChatGPT receives the canonical full report.
Each destination and part has its own status, receipt, retry/UNKNOWN state, and
audit record. A report is `RECONCILED` only after every required destination
part has a verified receipt. Generation, export, handoff, and first-chunk
success never imply delivery.

`OfflineReportAdapter` is explicitly a test double. `LocalHandoffAdapter`
remains unconfirmed until a trusted platform adapter records a receipt bound to
the report digest, destination, revision, and part. Credentials are never
stored in reports or logs.

Report delivery uses durable per-part leases and attempt IDs. The attempt intent
is committed before an adapter is called; expired leases become `UNKNOWN` and
are never automatically resent. Telegram reports use the typed Direct Telegram
transport, while ChatGPT remains pending/blocked until a trusted platform
adapter or operator attestation supplies a receipt bound to the report digest
and attempt.

The independent Claude review workflow is integrated from PR #24's
`automation/claude-review-bridge` at source head
`df1aca2ac9c845e21f4118ccdf31323db1ef48c5`, with checkout pinned to
`d23441a48e516b6c34aea4fa41551a30e30af803` and Claude Code Action pinned to
the verified peeled commit
`a874e9ecd7bb36efdad65429c6b35815f5a08f10` for tag object
`50b26a71effe456d50842a733597491c5636cb6f`. It runs for same-repository PR
events; after bot-authored updates, an owner may submit a PR review whose body is
`@claude review <40-character-head-sha>`. The workflow
re-fetches the PR and rejects stale SHA, fork, branch, or malformed requests
before secrets are exposed. This review-only integration does not modify PR #24.
