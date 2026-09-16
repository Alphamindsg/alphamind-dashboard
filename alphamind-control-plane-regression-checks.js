"use strict";

var assert = require("node:assert/strict");
var fs = require("node:fs");
var path = require("node:path");
var policy = require("./alphamind-authority-policy.js");
var validator = require("./alphamind-control-plane-validator.js");

function readFixture(name) {
  return JSON.parse(fs.readFileSync(path.join(__dirname, "test", "fixtures", name), "utf8"));
}

var valid = readFixture("control-plane-valid.json");
valid.records.forEach(function (record, index) {
  assert.deepEqual(
    validator.validateRecord(record),
    [],
    "valid fixture " + index + " must pass"
  );
});

var invalid = readFixture("control-plane-invalid.json");
invalid.cases.forEach(function (testCase) {
  var errors = validator.validateRecord(testCase.record);
  assert.ok(
    errors.indexOf(testCase.expected_error) !== -1,
    testCase.name + " expected " + testCase.expected_error + " but received " + JSON.stringify(errors)
  );
});

var workers = Object.values(policy.WORKER_KIND);
var levels = Object.values(policy.AUTHORITY_LEVEL);
workers.forEach(function (worker) {
  levels.forEach(function (level) {
    policy.HARD_DENY_ACTIONS.forEach(function (action) {
      assert.equal(
        policy.canWorkerAct(worker, level, action),
        worker === policy.WORKER_KIND.HUMAN,
        worker + " must fail closed for " + action
      );
    });
  });
});

[-1, 5, 1.5, NaN, Infinity].forEach(function (level) {
  workers.forEach(function (worker) {
    assert.equal(policy.canWorkerAct(worker, level, "UPDATE_INTERNAL_STATE"), false);
  });
});

["UNKNOWN", "", null, undefined].forEach(function (worker) {
  assert.equal(policy.canWorkerAct(worker, policy.AUTHORITY_LEVEL.L0_OBSERVE, "READ"), false);
});

var privateFields = [
  "account_balance", "bank_account", "card_number", "cpf", "insurance_policy",
  "liability", "personal_transaction", "private_financial_document", "safe_to_spend"
];
privateFields.forEach(function (field) {
  var envelope = {
    record_type: "RESEARCH_ENVELOPE",
    public_research_only: true,
    exact_head_sha: "1111111111111111111111111111111111111111"
  };
  envelope[field] = "sensitive";
  assert.ok(
    validator.validateResearchEnvelope(envelope).indexOf("private_finance_field:" + field) !== -1,
    field + " must not enter public AlphaMind research"
  );
});

console.log("AlphaMind control-plane invariant checks passed.");
