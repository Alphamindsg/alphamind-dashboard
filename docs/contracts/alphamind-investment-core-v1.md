# AlphaMind Investment Core Contract v1

Status: proposed implementation contract for issue #6.

## Authority boundary

AlphaMind is an evidence-driven investment research and decision-support system. It has no brokerage transaction authority. AlphaMind FX owns FX trading/execution authority under its separate gates. Personal Finance OS owns private user holdings, CPF, insurance, liabilities, goals and suitability. AlphaMind may export sanitized, versioned research envelopes to PFO but must not ingest or persist private PFO financial data in the public dashboard.

## Evidence contract

Every material research claim MUST be representable as:

```json
{
  "evidence_id": "string",
  "instrument_id": "string|null",
  "claim": "string",
  "evidence_class": "FACT|ESTIMATE|OPINION|MARKET_PRICE|MODEL_OUTPUT|UNVERIFIED",
  "source": {"provider":"string","source_id":"string|null","url":"string|null"},
  "published_at": "timestamp|null",
  "effective_at": "timestamp|null",
  "retrieved_at": "timestamp",
  "content_hash": "string|null",
  "freshness": "CURRENT|AGING|STALE|UNKNOWN",
  "confidence": "HIGH|MEDIUM|LOW|UNKNOWN",
  "contradicts": ["evidence_id"],
  "supersedes": ["evidence_id"]
}
```

STALE or UNKNOWN evidence cannot silently be rendered as current. Material contradictions remain visible. Insufficient evidence can force abstention.

## Instrument identity

Canonical identity is independent of display ticker. Store stable internal ID plus supported identifiers, exchange, currency, asset class, issuer/fund family, aliases and effective-dated corporate-action identity changes. Historical observations MUST retain the identity that was valid at the observation time.

## Thesis ledger

A thesis is append-only by version. Corrections create a superseding version; history is not overwritten.

Required fields:
- thesis_id and version
- instrument_id
- recommendation: WATCH | CONSIDER_BUY | HOLD | CONSIDER_TRIM_SELL | AVOID | INSUFFICIENT_EVIDENCE
- horizon
- role: GROWTH | INCOME | DEFENSIVE | OPPORTUNITY
- thesis
- key assumptions
- valuation method/range and assumption references
- catalysts
- downside/bear case
- invalidation conditions
- strengthen/weaken/change conditions
- evidence IDs
- confidence and uncertainty
- created_at
- process/model/author provenance
- supersedes_version

A news/event assessment uses THESIS_UNCHANGED | STRENGTHENED | WEAKENED | MATERIAL_REVIEW_REQUIRED. No headline, model, technical indicator or social post can directly emit an executable BUY/SELL action.

## Valuation contract

Valuation is asset-specific and assumption-driven. Every valuation result records method, inputs, source/effective dates, sensitivity cases, output range and uncertainty. Unsupported inputs cause partial/insufficient evidence rather than fabricated precision.

Minimum adapter families:
- Equity: earnings/FCF/margins/growth/ROIC, historical/peer multiples, DCF where supportable.
- REIT: NAV/P-NAV, distribution yield/coverage, leverage, debt maturity/rate exposure, occupancy/WALE where available.
- ETF: holdings/concentration, fees/tracking, factor/sector/geography and underlying valuation where meaningful.
- Fixed income/cash-like: yield, duration, credit, rate, reinvestment and liquidity risk.

## Decision journal and outcome review

Material decisions are timestamped before outcomes. Outcome review records what occurred, thesis correctness, valuation error, timing error, missed evidence, unexpected events and process lessons. Process quality and lucky/unlucky outcome are separate fields. No automatic self-modification occurs from outcome data.

## Research challenge

Material recommendations SHOULD include bull/base/bear cases and the strongest counterargument. Independent model/reviewer disagreement is retained, not averaged into a consensus score. Deterministic evidence and validated calculations outrank model opinion.

## Paper research portfolio

Any AlphaMind research portfolio is non-executing and separate from real PFO holdings. Recommendation timestamps are immutable for evaluation. Benchmarking must prevent look-ahead and survivorship bias where practicable and disclose transaction-cost assumptions.

## Privacy tests

The AlphaMind repository MUST reject/flag contracts containing private PFO fields such as bank account numbers, private balances, CPF balances, insurance policy identifiers, personal liabilities or transaction history. Cross-system suitability occurs inside PFO.

## Required first-slice tests

1. evidence schema accepts valid classes and rejects unknown classes;
2. stale evidence cannot satisfy a current-evidence requirement;
3. contradictory evidence remains linked and visible;
4. thesis versions are append-only/superseding;
5. invalid recommendation transition/action authority cannot create a trade command;
6. valuation range retains assumptions and uncertainty;
7. corporate-action identity fixture preserves historical identity;
8. PFO-private-field leakage fixture fails;
9. outcome review cannot rewrite original decision timestamp/evidence;
10. replay of the same evidence/thesis command is idempotent.

## Release boundary

Branch/PR only. No main merge, production mutation, brokerage transaction authority or movement of private PFO data without the applicable owner gate. Exact-head CI/security/review evidence is required before promotion.