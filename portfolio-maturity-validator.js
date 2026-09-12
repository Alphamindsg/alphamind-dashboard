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
var DIMENSION_KEYS = Object.freeze(Object.keys(WEIGHTS));
var TOP_LEVEL_KEYS = Object.freeze([
  "schema_version",
  "repository",
  "exact_head_sha",
  "measured_at",
  "dimensions",
  "weighted_score",
  "outcomes",
  "release_state",
  "known_blockers"
]);
var REQUIRED_OUTCOME_KEYS = Object.freeze([
  "primary_kpi",
  "baseline",
  "current",
  "measurement_status"
]);
var ALLOWED_OUTCOME_KEYS = Object.freeze(REQUIRED_OUTCOME_KEYS.concat([
  "counterfactual",
  "notes"
]));

function isScore(value) {
  return Number.isFinite(value) && value >= 0 && value <= 100;
}

function hasExactKeys(object, expectedKeys) {
  if (!object || typeof object !== "object" || Array.isArray(object)) return false;
  var actual = Object.keys(object).sort();
  var expected = expectedKeys.slice().sort();
  if (actual.length !== expected.length) return false;
  for (var i = 0; i < expected.length; i += 1) {
    if (actual[i] !== expected[i]) return false;
  }
  return true;
}

function hasOnlyAllowedKeys(object, allowedKeys) {
  if (!object || typeof object !== "object" || Array.isArray(object)) return false;
  return Object.keys(object).every(function (key) {
    return allowedKeys.indexOf(key) !== -1;
  });
}

function hasRequiredKeys(object, requiredKeys) {
  if (!object || typeof object !== "object" || Array.isArray(object)) return false;
  return requiredKeys.every(function (key) {
    return Object.prototype.hasOwnProperty.call(object, key);
  });
}

function isOutcomeValue(value) {
  return value === null || typeof value === "number" || typeof value === "string";
}

function calculateWeightedScore(dimensions) {
  if (!hasExactKeys(dimensions, DIMENSION_KEYS)) return null;
  for (var i = 0; i < DIMENSION_KEYS.length; i += 1) {
    if (!isScore(dimensions[DIMENSION_KEYS[i]])) return null;
  }
  var total = DIMENSION_KEYS.reduce(function (sum, key) {
    return sum + dimensions[key] * WEIGHTS[key];
  }, 0);
  return Math.round(total * 100) / 100;
}

function validate(record) {
  var errors = [];
  if (!record || typeof record !== "object" || Array.isArray(record)) return ["record_invalid"];
  if (!hasOnlyAllowedKeys(record, TOP_LEVEL_KEYS)) errors.push("record_fields_invalid");
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
    if (!hasOnlyAllowedKeys(record.outcomes, ALLOWED_OUTCOME_KEYS)) errors.push("outcomes_fields_invalid");
    if (!hasRequiredKeys(record.outcomes, REQUIRED_OUTCOME_KEYS)) errors.push("outcomes_required_fields_missing");
    if (typeof record.outcomes.primary_kpi !== "string" || record.outcomes.primary_kpi.length === 0) errors.push("primary_kpi_invalid");
    if (!isOutcomeValue(record.outcomes.baseline)) errors.push("baseline_invalid");
    if (!isOutcomeValue(record.outcomes.current)) errors.push("current_invalid");
    if (OUTCOME_STATES.indexOf(record.outcomes.measurement_status) === -1) errors.push("measurement_status_invalid");
    if (record.outcomes.counterfactual !== undefined && !isOutcomeValue(record.outcomes.counterfactual)) {
      errors.push("counterfactual_invalid");
    }
    if (record.outcomes.notes !== undefined && typeof record.outcomes.notes !== "string") errors.push("notes_invalid");
    if (record.release_state === "READY" && record.outcomes.measurement_status !== "MEASURED") {
      errors.push("ready_requires_measured_outcome");
    }
  }

  var blockersValid = record.known_blockers === undefined ||
    (Array.isArray(record.known_blockers) && record.known_blockers.every(function (item) {
      return typeof item === "string";
    }));
  if (!blockersValid) errors.push("known_blockers_invalid");
  if (record.release_state === "READY") {
    if (!blockersValid) {
      errors.push("ready_with_unknown_blockers");
    } else if (Array.isArray(record.known_blockers) && record.known_blockers.length > 0) {
      errors.push("ready_with_known_blockers");
    }
  }
  return errors;
}

module.exports = Object.freeze({
  WEIGHTS: WEIGHTS,
  RELEASE_STATES: RELEASE_STATES,
  OUTCOME_STATES: OUTCOME_STATES,
  DIMENSION_KEYS: DIMENSION_KEYS,
  calculateWeightedScore: calculateWeightedScore,
  validate: validate
});
