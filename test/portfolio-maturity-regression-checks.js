"use strict";

var assert = require("node:assert/strict");
var maturity = require("../portfolio-maturity-validator.js");

var dimensions = {
  scope: 80,
  correctness: 90,
  reliability_recovery: 70,
  security: 85,
  ux: 75,
  automation: 88,
  real_world_validation: 60,
  cost_efficiency: 95
};

var score = maturity.calculateWeightedScore(dimensions);
assert.equal(score, 80.05);

var valid = {
  schema_version: "portfolio-maturity-v1",
  repository: "Alphamindsg/example",
  exact_head_sha: "1111111111111111111111111111111111111111",
  measured_at: "2026-09-12T04:00:00Z",
  dimensions: dimensions,
  weighted_score: score,
  outcomes: {
    primary_kpi: "verified useful outcomes",
    baseline: 10,
    current: 12,
    measurement_status: "MEASURED",
    counterfactual: 9
  },
  release_state: "VERIFIED",
  known_blockers: []
};
assert.deepEqual(maturity.validate(valid), []);

var mismatch = Object.assign({}, valid, { weighted_score: 99 });
assert.ok(maturity.validate(mismatch).indexOf("weighted_score_mismatch") !== -1);

var badHead = Object.assign({}, valid, { exact_head_sha: "main" });
assert.ok(maturity.validate(badHead).indexOf("exact_head_sha_invalid") !== -1);

var invalidDimension = JSON.parse(JSON.stringify(valid));
invalidDimension.dimensions.correctness = 101;
assert.ok(maturity.validate(invalidDimension).indexOf("dimensions_invalid") !== -1);

var extraDimension = JSON.parse(JSON.stringify(valid));
extraDimension.dimensions.unapproved_dimension = 100;
assert.equal(maturity.calculateWeightedScore(extraDimension.dimensions), null);
assert.ok(maturity.validate(extraDimension).indexOf("dimensions_invalid") !== -1);

var missingDimension = JSON.parse(JSON.stringify(valid));
delete missingDimension.dimensions.security;
assert.equal(maturity.calculateWeightedScore(missingDimension.dimensions), null);
assert.ok(maturity.validate(missingDimension).indexOf("dimensions_invalid") !== -1);

var prematureReady = JSON.parse(JSON.stringify(valid));
prematureReady.release_state = "READY";
prematureReady.outcomes.measurement_status = "PARTIAL";
assert.ok(maturity.validate(prematureReady).indexOf("ready_requires_measured_outcome") !== -1);

var blockedReady = JSON.parse(JSON.stringify(valid));
blockedReady.release_state = "READY";
blockedReady.known_blockers = ["recovery certification missing"];
assert.ok(maturity.validate(blockedReady).indexOf("ready_with_known_blockers") !== -1);

["recovery certification missing", { blocker: "recovery" }, 1].forEach(function (malformedBlockers) {
  var malformedReady = JSON.parse(JSON.stringify(valid));
  malformedReady.release_state = "READY";
  malformedReady.known_blockers = malformedBlockers;
  var errors = maturity.validate(malformedReady);
  assert.ok(errors.indexOf("known_blockers_invalid") !== -1);
  assert.ok(errors.indexOf("ready_with_unknown_blockers") !== -1);
});

var malformedBlockerItem = JSON.parse(JSON.stringify(valid));
malformedBlockerItem.known_blockers = ["valid", { invalid: true }];
assert.ok(maturity.validate(malformedBlockerItem).indexOf("known_blockers_invalid") !== -1);

assert.equal(maturity.calculateWeightedScore(null), null);
assert.deepEqual(maturity.validate(null), ["record_invalid"]);

console.log("Portfolio maturity regression checks passed.");
