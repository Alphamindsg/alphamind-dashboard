"use strict";

(function (root) {
  var WORKER_KIND = Object.freeze({
    ENGINE: "ENGINE",
    BOT: "BOT",
    AI: "AI",
    HUMAN: "HUMAN"
  });

  var AUTHORITY_LEVEL = Object.freeze({
    L0_OBSERVE: 0,
    L1_ANALYZE: 1,
    L2_REVERSIBLE: 2,
    L3_CONSEQUENTIAL: 3,
    L4_FINANCIAL_IRREVERSIBLE: 4
  });

  var EVIDENCE_FRESHNESS = Object.freeze({
    CURRENT: "CURRENT",
    AGING: "AGING",
    STALE: "STALE",
    UNKNOWN: "UNKNOWN"
  });

  var RECOMMENDATION = Object.freeze({
    WATCH: "WATCH",
    CONSIDER_BUY: "CONSIDER_BUY",
    HOLD: "HOLD",
    CONSIDER_TRIM_SELL: "CONSIDER_TRIM_SELL",
    AVOID: "AVOID",
    INSUFFICIENT_EVIDENCE: "INSUFFICIENT_EVIDENCE"
  });

  var HARD_DENY_ACTIONS = Object.freeze([
    "BROKER_ORDER",
    "TRANSFER_FUNDS",
    "CHANGE_RISK_CONSTITUTION",
    "CHANGE_PRODUCTION_SECRET",
    "DELETE_AUDIT_EVIDENCE",
    "SELF_MODIFY_PRODUCTION"
  ]);

  function isKnownWorkerKind(kind) {
    return Object.prototype.hasOwnProperty.call(WORKER_KIND, kind);
  }

  function isHardDenied(action) {
    return HARD_DENY_ACTIONS.indexOf(action) !== -1;
  }

  function canWorkerAct(workerKind, authorityLevel, action) {
    if (!isKnownWorkerKind(workerKind)) return false;
    if (!Number.isInteger(authorityLevel) || authorityLevel < 0 || authorityLevel > 4) return false;

    if (isHardDenied(action)) {
      return workerKind === WORKER_KIND.HUMAN;
    }

    if (workerKind === WORKER_KIND.AI) {
      return authorityLevel <= AUTHORITY_LEVEL.L1_ANALYZE;
    }

    if (workerKind === WORKER_KIND.BOT) {
      return authorityLevel <= AUTHORITY_LEVEL.L2_REVERSIBLE;
    }

    if (workerKind === WORKER_KIND.ENGINE) {
      return authorityLevel <= AUTHORITY_LEVEL.L2_REVERSIBLE;
    }

    return workerKind === WORKER_KIND.HUMAN;
  }

  function evidenceCanSupportCurrentDecision(evidence) {
    if (!evidence || typeof evidence !== "object") return false;
    if (!evidence.evidence_id || !evidence.evidence_class) return false;
    if (evidence.freshness !== EVIDENCE_FRESHNESS.CURRENT) return false;
    if (!evidence.retrieved_at) return false;
    return true;
  }

  function deriveRecommendation(input) {
    if (!input || typeof input !== "object") return RECOMMENDATION.INSUFFICIENT_EVIDENCE;
    var evidence = Array.isArray(input.evidence) ? input.evidence : [];
    if (evidence.length === 0) return RECOMMENDATION.INSUFFICIENT_EVIDENCE;
    if (!evidence.every(evidenceCanSupportCurrentDecision)) {
      return RECOMMENDATION.INSUFFICIENT_EVIDENCE;
    }
    if (input.materialContradiction === true) return RECOMMENDATION.INSUFFICIENT_EVIDENCE;
    if (input.requestedRecommendation && Object.prototype.hasOwnProperty.call(RECOMMENDATION, input.requestedRecommendation)) {
      return RECOMMENDATION[input.requestedRecommendation];
    }
    return RECOMMENDATION.WATCH;
  }

  function shouldEscalateToAI(task) {
    if (!task || typeof task !== "object") return false;
    if (task.deterministicResultAvailable === true) return false;
    return task.requiresSynthesis === true ||
      task.materialContradiction === true ||
      task.ambiguity === "HIGH" ||
      task.novelty === "HIGH";
  }

  function classifyBotHealth(lastSuccessAt, now, maxAgeMs, blocked) {
    if (blocked === true) return "BLOCKED";
    if (!lastSuccessAt || !now || !Number.isFinite(maxAgeMs) || maxAgeMs <= 0) return "UNKNOWN";
    var age = new Date(now).getTime() - new Date(lastSuccessAt).getTime();
    if (!Number.isFinite(age) || age < 0) return "UNKNOWN";
    if (age <= maxAgeMs) return "HEALTHY";
    if (age <= maxAgeMs * 2) return "DEGRADED";
    return "FAILED";
  }

  var api = Object.freeze({
    WORKER_KIND: WORKER_KIND,
    AUTHORITY_LEVEL: AUTHORITY_LEVEL,
    EVIDENCE_FRESHNESS: EVIDENCE_FRESHNESS,
    RECOMMENDATION: RECOMMENDATION,
    HARD_DENY_ACTIONS: HARD_DENY_ACTIONS,
    canWorkerAct: canWorkerAct,
    evidenceCanSupportCurrentDecision: evidenceCanSupportCurrentDecision,
    deriveRecommendation: deriveRecommendation,
    shouldEscalateToAI: shouldEscalateToAI,
    classifyBotHealth: classifyBotHealth
  });

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.AlphaMindAuthorityPolicy = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
