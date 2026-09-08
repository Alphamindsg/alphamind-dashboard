# NOTIFY-001 operator guide

The notification gateway is a separate server-side Python package. It is not
loaded by the browser and never accepts a destination or URL from an event.
Events are accepted only from configured trusted producers (the local default
is `dashboard`) and are persisted in SQLite before Telegram side effects.

## Protected configuration

Only environment names are documented here:

- `ALPHAMIND_TELEGRAM_BOT_TOKEN`
- `ALPHAMIND_TELEGRAM_CHAT_ID`
- `ALPHAMIND_NOTIFICATION_STATE`
- producer authentication configuration (the deployment's secret-manager
  mapping; no value belongs in source, issues, logs, or chat)

Keep the state path on durable protected storage. `python -m
notification_gateway doctor` reports presence only and exits nonzero when
activation is not ready. Set `ALPHAMIND_NOTIFICATION_STATE` to an absolute
durable path; the CLI refuses a missing path and never creates a repository-root
default. `health` reports queue, dead-letter, `PAUSED`, and `BLOCKED` state
without secrets.

Create a bot in BotFather with `/newbot`, start a private chat with it, and
discover the chat ID through a secured operator-only process. Put both values
in the deployment secret manager. Do not run a live test until protected
activation is approved. The default worker has no fallback provider; TaskNotify
is intentionally disabled unless separately configured.

## Safety and reconciliation

INFO and routine WARNING activity is silent unless an owner action is explicit.
OWNER_ACTION and CRITICAL messages contain what happened, impact, minimum owner
action, and repository/head SHA/PR/issue/run provenance. Telegram sends are
plain text and bounded to Telegram's message limit.

A timeout or crash after a possible send is `UNKNOWN`: the event is quarantined,
never automatically resent, and requires explicit operator evidence before
reconciliation. Use the bounded CLI form
`python -m notification_gateway reconcile --event-id EVENT_ID --decision
delivered --evidence RUN_REF` only after independently checking the evidence.
This records `RECONCILED`, not a fabricated Telegram receipt. Dead letters, leases, fencing, retry budgets, 429
`retry_after`, shared provider cooldown, and redaction are durable controls.
Apply **PREVENT → DETECT EARLY → ISOLATE → REMEDIATE → VERIFY → RECONCILE →
RECORD → LEARN → REGRESSION GUARD**. This service does not grant merge,
deployment, capital, or production-database authority.

## Dual report workflow

Reports must contain `status`, `changes_since_previous`, `exact_head_evidence`,
`defects_blockers`, `tests_security_recovery`, `next_autonomous_work`, and
`owner_actions`. Submit a JSON fixture with:

```bash
ALPHAMIND_NOTIFICATION_STATE=/absolute/durable/path.sqlite3 \
  python -m notification_gateway report-submit --event report.json
```

This only records `GENERATED`. It does not claim either destination delivered.
Production delivery requires explicit ChatGPT and Telegram adapters that return
platform-confirmed receipts bound to the report ID, revision, part, and content
hash. For offline contract testing only:

```bash
ALPHAMIND_NOTIFICATION_STATE=/absolute/durable/path.sqlite3 \
  python -m notification_gateway report-worker --report-id report-1 \
  --revision 1 --offline-test-double
```

The local handoff adapter is intentionally unconfirmed and results in
`UNKNOWN`; it cannot fabricate ChatGPT success. Telegram failures preserve the
canonical report and ChatGPT delivery independently. Do not activate live
sends until protected approval is recorded.
