"use strict";

var fs = require("node:fs");
var validator = require("./alphamind-control-plane-validator.js");

var baseSha = process.env.BASE_SHA;
var headSha = process.env.HEAD_SHA;
var prNumber = Number(process.env.PR_NUMBER || "7");

var bundle = {
  record_type: "RELEASE_EVIDENCE",
  repository: process.env.GITHUB_REPOSITORY || "Alphamindsg/alphamind-dashboard",
  branch: process.env.GITHUB_HEAD_REF || process.env.GITHUB_REF_NAME || "unknown",
  pr_number: prNumber,
  base_sha: baseSha,
  exact_head_sha: headSha,
  generated_at: new Date().toISOString(),
  build: ["not-applicable:contract-pilot"],
  tests: [
    "node alphamind-authority-policy-regression-checks.js",
    "node alphamind-control-plane-regression-checks.js"
  ],
  ci: [
    "workflow:" + (process.env.GITHUB_WORKFLOW || "local"),
    "run_id:" + (process.env.GITHUB_RUN_ID || "local"),
    "run_attempt:" + (process.env.GITHUB_RUN_ATTEMPT || "local")
  ],
  security: [
    "least-privilege workflow",
    "hard-denied action matrix",
    "PFO privacy-boundary negative fixtures"
  ],
  dependencies: ["none:new"],
  migrations_or_schema_changes: [
    "docs/contracts/bot-control-plane-v1.schema.json",
    "docs/contracts/alphamind-research-envelope-v1.schema.json"
  ],
  recovery: ["recovery PASS requires restore identity and evidence"],
  outstanding_risks: [
    "Claude independent review pending",
    "Codex Security not invoked for this low-runtime contract slice",
    "production authorization not requested"
  ],
  independent_review: null,
  owner_authorization: null,
  production_authorization_status: "NOT_REQUESTED",
  rollout_plan: "pilot evidence only; portfolio rollout requires independent review",
  rollback_plan: "revert the pilot commits on the feature branch"
};

var errors = validator.validateReleaseEvidence(bundle);
if (errors.length) {
  console.error("Release evidence validation failed:", errors);
  process.exit(1);
}

fs.writeFileSync("release-evidence.json", JSON.stringify(bundle, null, 2) + "\n");
console.log(JSON.stringify(bundle, null, 2));
console.log("Exact-head release evidence generated and validated.");
