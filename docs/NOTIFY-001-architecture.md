# NOTIFY-001 architecture

`notification_gateway/` is a standard-library-only server-side package. A
strict event schema and producer allowlist feed a transactional SQLite
event/outbox store. The worker claims a fenced lease, formats safe plaintext,
and sends through Direct Telegram only. It records the receipt before
verification; ambiguous transport outcomes become `UNKNOWN` and are not
resent.

The gateway is deliberately separate from the static Dashboard frontend.
There are no browser secrets, arbitrary destinations, arbitrary URLs, live
Telegram tests, Actions artifacts used as state, or automatic fallback after
an ambiguous send. The CLI provides presence-only doctor, persistent queue
health, and one-worker processing commands.

The package supports the repository's assurance vocabulary by carrying exact
repository, head SHA, PR, issue, and run provenance as evidence. Evidence is
descriptive and does not grant authority. Existing Dashboard checks and the
evidence/Claude workstreams remain unchanged.
