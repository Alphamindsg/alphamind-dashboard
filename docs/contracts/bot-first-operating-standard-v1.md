# Bot-First Operating Standard v1 — AlphaMind

Status: proposed implementation contract for #8/#9/#10/#11/#12/#13 and extension of #6.

## Core rule
Deterministic engines first; routine bots/workers second; validated statistical/ML components where justified; AI only for bounded research/synthesis/challenge where it adds measurable value; explicit authority gates for consequential operations.

AlphaMind is research/advisory only. It has no brokerage transaction authority and stores no private PFO financial data.

## Worker classes and authority
Classes: `DETERMINISTIC_ENGINE`, `BOT_WORKER`, `MODEL_COMPONENT`, `AI_ANALYST`, `HUMAN_AUTHORITY`.
Authority: `L0_OBSERVE`, `L1_ANALYSE`, `L2_REVERSIBLE_INTERNAL`, `L3_CONSEQUENTIAL_EXTERNAL`, `L4_FINANCIAL_IRREVERSIBLE`.
AlphaMind AI/bots are not granted L4 and cannot emit executable trade commands.

Authoritative deterministic domains include evidence freshness/validation, instrument identity, point-in-time lineage, valuation arithmetic, portfolio-research calculations, schema validation and release-policy checks. AI may synthesize thesis, explain, identify contradictions and produce bull/base/bear challenge but cannot turn one headline/model/indicator into authority.

## Bot registry / health / exception-first control
Every engine/bot/provider/model call site records identity, class, authority, owner, trigger, dependencies, exact software/config/data/model/provider versions, last/next run, heartbeat, freshness, latency, retry/dead-letter state, evidence pointer, cost and owner-action class.

Health: `HEALTHY | DEGRADED | BLOCKED | FAILED | PAUSED`. Silent missed runs or stale heartbeats are failures.
Owner action: `NO_OWNER_ACTION | OWNER_REVIEW | OWNER_APPROVAL_REQUIRED | SECURITY_HOLD | RESEARCH_HOLD`.

## Evidence graph
Material research reconstructs:
`Source/Evidence -> Valuation/Research -> Thesis Version -> Independent Challenge/Disagreement -> Recommendation or Abstention -> Later Outcome -> Attribution -> Improvement Proposal`.
All links are append-only/superseding and point-in-time reproducible. Disagreement is preserved, not averaged into fake consensus.

## Abstention and counterfactual learning
`INSUFFICIENT_EVIDENCE` is a first-class recommendation. Track accepted ideas, rejected ideas and abstentions against later outcomes where an unbiased observation is possible. Separate process quality from outcome luck. Do not retroactively replace the original evidence with data learned later.

## Shadow board
New models, providers, valuation variants, thesis policies and research rules run non-authoritatively on identical versioned evidence. Compare evidence fidelity, calibration, abstention quality, false positives/negatives, contradiction handling, latency, cost and stability. Shadow output cannot become authoritative until predefined benchmark, regression, exact-head security/CI and independent-review gates pass.

## Threat model / FMEA
Maintain threats and failure modes for source poisoning, stale data, identity/corporate-action errors, look-ahead leakage, private PFO leakage, model/prompt injection, provider outage, fabricated precision, policy bypass, supply chain and rollback. High severity modes require detection, containment, safe state, recovery and regression fixture.

## Recovery certification
Prove—not assume—backup/restore of research/evidence state, replay/idempotency, cache/version invalidation, provider outage degradation, rollback and audit preservation. Record exact SHA/config/data identity and drill result.

## Economic-value routing
AI escalation records why deterministic handling was insufficient. Measure deterministic completion rate, AI escalation rate, cost/latency per call site, useful thesis changes, avoided bad calls where defensible, and model/provider quality. Cost reduction never weakens evidence/security gates.

## Opportunity cost contract
Research candidates are compared to approved alternatives/cash, not in isolation. Export only sanitized, versioned envelopes to PFO containing attractiveness, role, horizon, valuation/evidence, uncertainty, liquidity/risk notes and alternatives. PFO alone evaluates private suitability/capital allocation across HDB/emergency/CPF-SRS/Creator/FX/investments/cash.

## Controlled improvement
`Observe -> Detect -> Research -> Propose -> Branch -> Test -> Shadow/Benchmark -> Independent Challenge -> Release Gate -> Deploy if authorized -> Monitor/Rollback`.
No uncontrolled production self-modification.

## Release Evidence Bundle
Record repository, base SHA, exact head SHA, build/tests, security/dependencies, data/schema changes, recovery evidence, outstanding risks, independent review, rollout/rollback and applicable owner gate.

## Initial executable slice
Implement machine-readable bot/authority/health/evidence/recovery/release schemas and deterministic tests for denied authority, stale heartbeat/evidence, contradiction preservation, private-data leakage, append-only thesis/outcome history, idempotent replay and shadow non-authority.