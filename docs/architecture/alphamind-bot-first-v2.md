# AlphaMind Bot-First Architecture v2

Status: proposed target architecture derived from the AlphaMind CTO/Master Proposal and issue #6.

## Design law

AlphaMind is bot-first and deterministic-first. AI is a bounded intelligence service, not the operating substrate and not the final authority for financial or irreversible actions.

Priority order:

1. deterministic rule/calculation/database operation;
2. bot/workflow automation;
3. statistical/ML model where independently validated;
4. AI reasoning only when synthesis, ambiguity, contradiction, novelty or qualitative judgment materially benefits from it;
5. authority/risk gate before consequential action;
6. human governance for constitutional, capital-mandate, new-broker, new-asset-class, production-security and other explicitly reserved decisions.

## Four worker classes

### Deterministic engines
Authoritative for reproducible state/calculation domains. Examples: data quality, instrument identity, valuation arithmetic, portfolio state, policy evaluation, risk constraints, accounting/treasury records, replay/backtest mechanics, order state, reconciliation, performance/TCA, audit and kill controls.

### Bots/workers
Cheap, routine, retryable automation. Examples: price/news/fundamental/corporate-action collectors, schedulers, watchlist monitoring, strategy-health monitoring, report generation, alerting, backup/restore verification, cost monitoring and recovery/reconciliation jobs.

### AI intelligence
Bounded reasoning only. Examples: fundamental analyst, macro analyst, news-materiality analyst, thesis analyst, strategy researcher, devil's advocate and postmortem analyst. AI output is structured evidence/opinion; it is never binding risk authority or a brokerage command.

### Human governance
Owns constitution, risk appetite, capital mandates, phase promotions, new live brokers, new asset classes, material autonomous-authority changes, production security policy, emergency recovery after hard stops and other non-delegable decisions.

## Authority levels

- L0 Observe: read, monitor, retrieve.
- L1 Analyze: calculate, classify, synthesize, propose.
- L2 Reversible internal action: queue, draft, cache, create/supersede internal research records under idempotent controls.
- L3 Consequential external action: publishing/contact or material external state change.
- L4 Financial/irreversible action: orders, transfers, destructive authoritative mutation, constitutional/risk/security changes.

Default maximums in general AlphaMind:
- AI: L1.
- Bot: L2.
- Deterministic engine: L2 unless a separately approved execution subsystem grants narrowly scoped authority.
- Human governance: L4 subject to secure process.

General AlphaMind currently has no live brokerage execution authority. AlphaMind FX remains separately governed.

## Bot operating standard

Every long-running bot MUST implement:

Trigger -> input validation -> idempotency/dedupe -> lock/lease where needed -> execute -> verify result -> persist evidence -> update health -> retry safely -> dead-letter/escalate if unresolved.

Required health states:
HEALTHY | DEGRADED | BLOCKED | FAILED | PAUSED | UNKNOWN.

Required telemetry:
- bot/workflow ID and version;
- exact software SHA/config version;
- last attempt and last success;
- duration;
- retry count;
- input/output identity/hash where appropriate;
- dependency health;
- failure reason;
- next scheduled run;
- cost when non-trivial.

Silent failure is a release-blocking defect for critical workflows.

## AI escalation policy

AI is not called merely because a task exists. Escalate only when deterministic output is unavailable and one or more are true:
- synthesis across heterogeneous evidence is required;
- material evidence conflicts;
- ambiguity is high;
- novelty/out-of-distribution condition is high;
- qualitative challenge materially improves decision quality.

AI outputs MUST be schema-valid, provenance-linked and independently validated for protected fields. Models do not receive unrestricted tool access. Model/tool routing is default-deny and capability-scoped.

## Evidence, decision and outcome chain

Every material recommendation MUST be reconstructible through:

Evidence -> Thesis Version -> Challenge -> Decision Record -> Authority Result -> Action/Abstention -> Outcome -> Attribution -> Lesson -> Improvement Proposal.

Maintain separate ledgers for evidence, theses, decisions, incidents, experiments and outcomes. Summaries link back to primary records.

## Abstention as a first-class capability

`INSUFFICIENT_EVIDENCE` is a valid and desirable result. Measure:
- opportunities reviewed;
- recommendations issued;
- abstentions;
- abstention reasons;
- subsequent outcomes of abstained/rejected opportunities.

Never optimize the system to maximize recommendation count.

## Counterfactual and rejection learning

Track accepted, rejected and abstained opportunities. Compare later outcomes while controlling for horizon and eligibility. Evaluate whether filters/risk/challenge layers add value rather than merely reducing activity.

Do not infer causality from tiny samples. Any policy change resulting from outcome analysis follows the controlled improvement lifecycle.

## Shadow/champion-challenger

New models, prompts, research policies or scoring systems first run in shadow when practical. Production remains unchanged while challenger outputs are logged against identical inputs. Compare calibration, abstention quality, false-positive/false-negative behavior, cost, latency and stability before promotion.

AI agreement is not correctness; disagreement is retained as evidence.

## Opportunity-cost engine

A research recommendation should compare an opportunity against relevant alternatives and cash/no-action, not only against its own past price. AlphaMind ranks investment attractiveness; Personal Finance OS separately evaluates user-specific capital suitability versus liquidity, housing, CPF/SRS, sidelines and other personal objectives.

## Exception-first owner operations

Normal operation stays quiet. Owner-facing output prioritizes:
- OWNER ACTION REQUIRED;
- OWNER APPROVAL REQUIRED;
- SECURITY/RISK HOLD;
- DEGRADED/BLOCKED critical workflow;
- material thesis change;
- high-value new opportunity;
- recovery completed after incident.

Routine success is summarized, not spammed.

## Recovery and resilience certification

Critical workflows need evidence that:
- backups exist;
- restore works;
- replay is deterministic where required;
- duplicate events do not duplicate actions;
- interrupted jobs recover safely;
- stale/missing data fails closed;
- release rollback works;
- audit/evidence remains intact;
- broker/external-state reconciliation is possible in execution-enabled systems.

A backup without a tested restore does not count as recovery evidence.

## Cost and value accounting

Measure per workflow/call site:
- deterministic completion rate;
- AI escalation rate;
- human escalation rate;
- model/provider cost;
- latency/failure rate;
- cache hit rate;
- accepted thesis changes;
- incremental quality versus deterministic baseline where measurable.

Remove or downgrade AI where it does not outperform a cheaper/reproducible alternative.

## Controlled improvement lifecycle

Observe -> Diagnose -> Research alternatives -> Benchmark -> Propose -> Implement on branch -> Test -> Independent challenge -> Release evidence -> Owner/authority gate where applicable -> Deploy -> Monitor -> Retain/Roll back.

No autonomous production self-modification.

## AlphaMind / AlphaMind FX / PFO separation

AlphaMind: public/non-private investment research, thesis, valuation, market/news intelligence, non-executing research portfolio.

AlphaMind FX: FX-specific research-to-execution machine with independent non-bypassable trading/risk/capital gates.

Personal Finance OS: private financial source of truth and suitability/capital-allocation authority for the owner. It receives sanitized/versioned AlphaMind research envelopes; AlphaMind must not ingest private PFO balances/transactions/CPF/insurance data into the public dashboard.

## Release acceptance additions

Before this architecture is promoted beyond contract stage:
- deterministic authority-policy tests pass;
- hard-denied actions cannot be performed by AI/bots;
- stale/contradictory evidence forces safe handling;
- bot health can distinguish healthy/degraded/failed/blocked;
- AI escalation is suppressed when deterministic result exists;
- privacy leakage fixtures fail closed;
- exact-head CI/security evidence exists;
- independent review has been captured;
- no main merge or production authority is implied by documentation alone.
