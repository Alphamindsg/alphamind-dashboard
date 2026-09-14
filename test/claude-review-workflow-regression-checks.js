"use strict";

var assert = require("node:assert/strict");
var fs = require("node:fs");

function read(path) {
  return fs.readFileSync(path, "utf8");
}

function parseAllowedBots(workflowSource) {
  var match = workflowSource.match(/^\s*allowed_bots:\s*([^\n#]+?)\s*$/m);
  return match ? match[1].split(",").map(function (value) {
    return value.trim().replace(/^['"]|['"]$/g, "");
  }).filter(Boolean) : [];
}

function canReachReview(policy) {
  if (!policy.sameRepository) return false;
  if (!policy.provenanceVerified) return false;
  if (!policy.oauthConfigured) return false;
  if (policy.actorType === "bot") return policy.allowedBots.indexOf(policy.actor) !== -1;
  return Boolean(policy.hasWritePermission);
}

var claudeWorkflow = read(".github/workflows/claude-review.yml");
var maturityWorkflow = read(".github/workflows/portfolio-maturity.yml");
var allowedBots = parseAllowedBots(claudeWorkflow);

assert.deepEqual(allowedBots, ["Copilot"]);
assert.equal(canReachReview({
  actor: "Copilot",
  actorType: "bot",
  sameRepository: true,
  provenanceVerified: true,
  oauthConfigured: true,
  hasWritePermission: false,
  allowedBots: allowedBots
}), true);
assert.equal(canReachReview({
  actor: "dependabot[bot]",
  actorType: "bot",
  sameRepository: true,
  provenanceVerified: true,
  oauthConfigured: true,
  hasWritePermission: false,
  allowedBots: allowedBots
}), false);
assert.equal(canReachReview({
  actor: "external-contributor",
  actorType: "user",
  sameRepository: false,
  provenanceVerified: true,
  oauthConfigured: true,
  hasWritePermission: false,
  allowedBots: allowedBots
}), false);
assert.equal(canReachReview({
  actor: "trusted-maintainer",
  actorType: "user",
  sameRepository: true,
  provenanceVerified: false,
  oauthConfigured: true,
  hasWritePermission: true,
  allowedBots: allowedBots
}), false);
assert.equal(canReachReview({
  actor: "trusted-maintainer",
  actorType: "user",
  sameRepository: true,
  provenanceVerified: true,
  oauthConfigured: false,
  hasWritePermission: true,
  allowedBots: allowedBots
}), false);

assert.match(claudeWorkflow, /if:\s+github\.event\.pull_request\.head\.repo\.full_name == github\.repository/);
assert.match(claudeWorkflow, /persist-credentials:\s+false/);
assert.match(claudeWorkflow, /ref:\s+\$\{\{\s*github\.event\.pull_request\.head\.sha\s*\}\}/);
assert.match(claudeWorkflow, /uses:\s+actions\/checkout@d23441a48e516b6c34aea4fa41551a30e30af803/);
assert.match(claudeWorkflow, /uses:\s+anthropics\/claude-code-action@a874e9ecd7bb36efdad65429c6b35815f5a08f10/);
assert.match(claudeWorkflow, /expected_commit="a874e9ecd7bb36efdad65429c6b35815f5a08f10"/);
assert.match(claudeWorkflow, /CLAUDE_CODE_OAUTH_TOKEN detected; running independent review\./);
assert.doesNotMatch(claudeWorkflow, /allowed_bots:\s*['"]?\*['"]?/);
assert.equal(claudeWorkflow.indexOf("allowed_non_write_users:") === -1, true);

assert.match(claudeWorkflow, /EXACT HEAD SHA:\s+\$\{\{\s*github\.event\.pull_request\.head\.sha\s*\}\}/);
assert.match(maturityWorkflow, /"\.github\/workflows\/claude-review\.yml"/);
assert.match(maturityWorkflow, /"test\/claude-review-workflow-regression-checks\.js"/);
assert.match(maturityWorkflow, /EXPECTED_HEAD_SHA:\s+\$\{\{\s*github\.event\.pull_request\.head\.sha \|\| github\.sha\s*\}\}/);
assert.match(maturityWorkflow, /node test\/claude-review-workflow-regression-checks\.js/);

console.log("Claude review workflow regression checks passed.");
