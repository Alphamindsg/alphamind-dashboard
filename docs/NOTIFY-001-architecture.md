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
