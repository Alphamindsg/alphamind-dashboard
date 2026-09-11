"use strict";

var assert = require("node:assert/strict");
var policy = require("./alphamind-authority-policy.js");

assert.equal(policy.canWorkerAct("AI", policy.AUTHORITY_LEVEL.L1_ANALYZE, "SYNTHESIZE_RESEARCH"), true);
assert.equal(policy.canWorkerAct("AI", policy.AUTHORITY_LEVEL.L2_REVERSIBLE, "QUEUE_REPORT"), false);
assert.equal(policy.canWorkerAct("BOT", policy.AUTHORITY_LEVEL.L2_REVERSIBLE, "QUEUE_REPORT"), true);
assert.equal(policy.canWorkerAct("BOT", policy.AUTHORITY_LEVEL.L3_CONSEQUENTIAL, "PUBLISH_EXTERNAL"), false);
assert.equal(policy.canWorkerAct("ENGINE", policy.AUTHORITY_LEVEL.L2_REVERSIBLE, "UPDATE_INTERNAL_STATE"), true);
assert.equal(policy.canWorkerAct("ENGINE", policy.AUTHORITY_LEVEL.L4_FINANCIAL_IRREVERSIBLE, "BROKER_ORDER"), false);
assert.equal(policy.canWorkerAct("HUMAN", policy.AUTHORITY_LEVEL.L4_FINANCIAL_IRREVERSIBLE, "BROKER_ORDER"), true);
assert.equal(policy.canWorkerAct("AI", policy.AUTHORITY_LEVEL.L1_ANALYZE, "BROKER_ORDER"), false);
assert.equal(policy.canWorkerAct("BOT", policy.AUTHORITY_LEVEL.L2_REVERSIBLE, "TRANSFER_FUNDS"), false);

var currentEvidence = {
  evidence_id: "e-1",
  evidence_class: "FACT",
  freshness: "CURRENT",
  retrieved_at: "2026-09-08T00:00:00Z"
};

assert.equal(policy.evidenceCanSupportCurrentDecision(currentEvidence), true);
assert.equal(policy.evidenceCanSupportCurrentDecision(Object.assign({}, currentEvidence, { freshness: "STALE" })), false);
assert.equal(policy.deriveRecommendation({ evidence: [] }), "INSUFFICIENT_EVIDENCE");
assert.equal(policy.deriveRecommendation({ evidence: [currentEvidence], materialContradiction: true }), "INSUFFICIENT_EVIDENCE");
assert.equal(policy.deriveRecommendation({ evidence: [currentEvidence], requestedRecommendation: "CONSIDER_BUY" }), "CONSIDER_BUY");

assert.equal(policy.shouldEscalateToAI({ deterministicResultAvailable: true, requiresSynthesis: true }), false);
assert.equal(policy.shouldEscalateToAI({ deterministicResultAvailable: false, requiresSynthesis: true }), true);
assert.equal(policy.shouldEscalateToAI({ deterministicResultAvailable: false, ambiguity: "HIGH" }), true);
assert.equal(policy.shouldEscalateToAI({ deterministicResultAvailable: false }), false);

assert.equal(policy.classifyBotHealth("2026-09-08T00:00:00Z", "2026-09-08T00:05:00Z", 600000, false), "HEALTHY");
assert.equal(policy.classifyBotHealth("2026-09-08T00:00:00Z", "2026-09-08T00:15:00Z", 600000, false), "DEGRADED");
assert.equal(policy.classifyBotHealth("2026-09-08T00:00:00Z", "2026-09-08T00:25:00Z", 600000, false), "FAILED");
assert.equal(policy.classifyBotHealth("2026-09-08T00:00:00Z", "2026-09-08T00:05:00Z", 600000, true), "BLOCKED");

console.log("AlphaMind authority policy regression checks passed.");
