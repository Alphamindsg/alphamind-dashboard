"use strict";

var WEIGHTS = Object.freeze({
  scope: 0.20,
  correctness: 0.20,
  reliability_recovery: 0.15,
  security: 0.10,
  ux: 0.10,
  automation: 0.10,
  real_world_validation: 0.10,
  cost_efficiency: 0.05
});

var RELEASE_STATES = Object.freeze([
  "UNVERIFIED",
  "TESTING",
  "FAILED",
  "REMEDIATING",
  "VERIFIED",
  "INDEPENDENT_REVIEW",
  "RELEASE_GATED",
  "OWNER_APPROVAL_REQUIRED",
  "READY"
]);

var OUTCOME_STATES = Object.freeze(["MEASURED", "PARTIAL", "UNKNOWN", "BLOCKED"]);

function isScore(value) {
  return Number.isFinite(value) && value >= 0 && value <= 100;
}

function calculateWeightedScore(dimensions) {
  if (!dimensions || typeof dimensions !== "object") return null;
  var keys = Object.keys(WEIGHTS);
  for (var i = 0; i < keys.length; i += 1) {
    if (!isScore(dimensions[keys[i]])) return null;
  }
  var total = keys.reduce(function (sum, key) {
    return sum + dimensions[key] * WEIGHTS[key];
  }, 0);
  return Math.round(total * 100) / 100;
}

function validate(record) {
  var errors = [];
  if (!record || typeof record !== "object" || Array.isArray(record)) return ["record_invalid"];
  if (record.schema_version !== "portfolio-maturity-v1") errors.push("schema_version_invalid");
  if (typeof record.repository !== "string" || record.repository.length < 3) errors.push("repository_invalid");
  if (typeof record.exact_head_sha !== "string" || !/^[0-9a-f]{40}$/.test(record.exact_head_sha)) errors.push("exact_head_sha_invalid");
  if (typeof record.measured_at !== "string" || !Number.isFinite(Date.parse(record.measured_at))) errors.push("measured_at_invalid");

  var expected = calculateWeightedScore(record.dimensions);
  if (expected === null) errors.push("dimensions_invalid");
  if (!isScore(record.weighted_score)) errors.push("weighted_score_invalid");
  if (expected !== null && isScore(record.weighted_score) && Math.abs(expected - record.weighted_score) > 0.01) {
    errors.push("weighted_score_mismatch");
  }

  if (RELEASE_STATES.indexOf(record.release_state) === -1) errors.push("release_state_invalid");

  if (!record.outcomes || typeof record.outcomes !== "object" || Array.isArray(record.outcomes)) {
    errors.push("outcomes_invalid");
  } else {
    if (typeof record.outcomes.primary_kpi !== "string" || record.outcomes.primary_kpi.length === 0) errors.push("primary_kpi_invalid");
    if (OUTCOME_STATES.indexOf(record.outcomes.measurement_status) === -1) errors.push("measurement_status_invalid");
    if (record.release_state === "READY" && record.outcomes.measurement_status !== "MEASURED") {
      errors.push("ready_requires_measured_outcome");
    }
  }

  if (record.release_state === "READY" && Array.isArray(record.known_blockers) && record.known_blockers.length > 0) {
    errors.push("ready_with_known_blockers");
  }
  return errors;
}

module.exports = Object.freeze({
  WEIGHTS: WEIGHTS,
  RELEASE_STATES: RELEASE_STATES,
  OUTCOME_STATES: OUTCOME_STATES,
  calculateWeightedScore: calculateWeightedScore,
  validate: validate
});
