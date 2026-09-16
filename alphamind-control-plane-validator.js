"use strict";

var HEALTH_STATES = ["HEALTHY", "DEGRADED", "BLOCKED", "FAILED", "PAUSED"];
var OWNER_ACTIONS = ["NO_OWNER_ACTION", "OWNER_REVIEW", "OWNER_APPROVAL_REQUIRED", "SECURITY_HOLD", "DOMAIN_HOLD"];
var WORKER_MAX_AUTHORITY = Object.freeze({
  DETERMINISTIC_ENGINE: 2,
  BOT_WORKER: 2,
  PROVIDER_ADAPTER: 2,
  MODEL_COMPONENT: 1,
  AI_ADVISER: 1,
  HUMAN_AUTHORITY: 4
});
var PRODUCTION_AUTHORIZATION = ["NOT_REQUESTED", "OWNER_APPROVAL_REQUIRED", "OWNER_APPROVED"];
var PRIVATE_FINANCE_FIELDS = [
  "account_balance", "bank_account", "card_number", "cpf", "insurance_policy",
  "liability", "personal_transaction", "private_financial_document", "safe_to_spend"
];

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isTimestamp(value) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function isSha(value) {
  return typeof value === "string" && /^[0-9a-f]{40}$/.test(value);
}

function requireFields(record, fields, errors) {
  fields.forEach(function (field) {
    if (!Object.prototype.hasOwnProperty.call(record, field)) errors.push("missing:" + field);
  });
}

function rejectUnknown(record, allowed, errors) {
  Object.keys(record).forEach(function (field) {
    if (allowed.indexOf(field) === -1) errors.push("unknown:" + field);
  });
}

function validateBotRuntime(record) {
  var errors = [];
  var allowed = [
    "record_type", "bot_id", "capability", "worker_class", "authority_level", "owner",
    "trigger", "dependencies", "software_version", "config_version", "data_contract_version",
    "model_provider_version", "last_started_at", "last_succeeded_at", "next_expected_at",
    "heartbeat_at", "health_state", "retry_count", "dead_letter_state", "evidence_pointer",
    "cost_amount", "cost_currency", "owner_action_class"
  ];
  requireFields(record, [
    "record_type", "bot_id", "worker_class", "authority_level", "health_state",
    "software_version", "last_succeeded_at", "next_expected_at", "owner_action_class"
  ], errors);
  rejectUnknown(record, allowed, errors);
  if (record.record_type !== "BOT_RUNTIME") errors.push("invalid:record_type");
  if (typeof record.bot_id !== "string" || !record.bot_id.trim()) errors.push("invalid:bot_id");
  if (!Object.prototype.hasOwnProperty.call(WORKER_MAX_AUTHORITY, record.worker_class)) errors.push("invalid:worker_class");
  if (!Number.isInteger(record.authority_level) || record.authority_level < 0 || record.authority_level > 4) {
    errors.push("invalid:authority_level");
  } else if (Object.prototype.hasOwnProperty.call(WORKER_MAX_AUTHORITY, record.worker_class) &&
      record.authority_level > WORKER_MAX_AUTHORITY[record.worker_class]) {
    errors.push("authority_exceeded:" + record.worker_class);
  }
  if (HEALTH_STATES.indexOf(record.health_state) === -1) errors.push("invalid:health_state");
  if (OWNER_ACTIONS.indexOf(record.owner_action_class) === -1) errors.push("invalid:owner_action_class");
  if (typeof record.software_version !== "string" || !record.software_version.trim()) errors.push("invalid:software_version");
  ["last_started_at", "last_succeeded_at", "next_expected_at", "heartbeat_at"].forEach(function (field) {
    if (record[field] !== null && record[field] !== undefined && !isTimestamp(record[field])) errors.push("invalid:" + field);
  });
  if (record.retry_count !== undefined && (!Number.isInteger(record.retry_count) || record.retry_count < 0)) errors.push("invalid:retry_count");
  if (record.cost_amount !== undefined && record.cost_amount !== null &&
      (typeof record.cost_amount !== "number" || !Number.isFinite(record.cost_amount) || record.cost_amount < 0)) {
    errors.push("invalid:cost_amount");
  }
  if (Array.isArray(record.dependencies) && new Set(record.dependencies).size !== record.dependencies.length) {
    errors.push("duplicate:dependencies");
  }
  return errors;
}

function validateRecovery(record) {
  var errors = [];
  var allowed = [
    "record_type", "certification_id", "repository", "exact_head_sha", "config_identity",
    "backup_identity", "performed_at", "result", "checks", "exceptions", "evidence"
  ];
  requireFields(record, ["record_type", "certification_id", "repository", "exact_head_sha", "performed_at", "result", "checks"], errors);
  rejectUnknown(record, allowed, errors);
  if (record.record_type !== "RECOVERY_CERTIFICATION") errors.push("invalid:record_type");
  if (!isSha(record.exact_head_sha)) errors.push("invalid:exact_head_sha");
  if (!isTimestamp(record.performed_at)) errors.push("invalid:performed_at");
  if (["PASS", "FAIL", "PARTIAL"].indexOf(record.result) === -1) errors.push("invalid:result");
  if (!Array.isArray(record.checks) || record.checks.length === 0) errors.push("invalid:checks");
  if (record.result === "PASS" && (!record.backup_identity || !Array.isArray(record.evidence) || record.evidence.length === 0)) {
    errors.push("unproven:recovery_pass");
  }
  return errors;
}

function validateReleaseEvidence(record) {
  var errors = [];
  var allowed = [
    "record_type", "repository", "branch", "pr_number", "base_sha", "exact_head_sha",
    "generated_at", "build", "tests", "ci", "security", "dependencies",
    "migrations_or_schema_changes", "recovery", "outstanding_risks", "independent_review",
    "owner_authorization", "production_authorization_status", "rollout_plan", "rollback_plan"
  ];
  requireFields(record, [
    "record_type", "repository", "branch", "pr_number", "base_sha", "exact_head_sha",
    "generated_at", "build", "tests", "ci", "security", "dependencies",
    "migrations_or_schema_changes", "recovery", "outstanding_risks",
    "production_authorization_status", "rollback_plan"
  ], errors);
  rejectUnknown(record, allowed, errors);
  if (record.record_type !== "RELEASE_EVIDENCE") errors.push("invalid:record_type");
  if (!isSha(record.base_sha)) errors.push("invalid:base_sha");
  if (!isSha(record.exact_head_sha)) errors.push("invalid:exact_head_sha");
  if (!isTimestamp(record.generated_at)) errors.push("invalid:generated_at");
  if (!Number.isInteger(record.pr_number) || record.pr_number < 1) errors.push("invalid:pr_number");
  ["build", "tests", "ci", "security", "dependencies", "migrations_or_schema_changes", "recovery", "outstanding_risks"].forEach(function (field) {
    if (!Array.isArray(record[field])) errors.push("invalid:" + field);
  });
  if (PRODUCTION_AUTHORIZATION.indexOf(record.production_authorization_status) === -1) errors.push("invalid:production_authorization_status");
  if (typeof record.rollback_plan !== "string" || !record.rollback_plan.trim()) errors.push("invalid:rollback_plan");
  if (record.production_authorization_status === "OWNER_APPROVED" && !record.owner_authorization) {
    errors.push("missing:owner_authorization");
  }
  return errors;
}

function validateResearchEnvelope(record) {
  var errors = [];
  if (!isObject(record)) return ["invalid:envelope"];
  if (record.record_type !== "RESEARCH_ENVELOPE") errors.push("invalid:record_type");
  if (record.public_research_only !== true) errors.push("invalid:public_research_only");
  if (!isSha(record.exact_head_sha)) errors.push("invalid:exact_head_sha");
  Object.keys(record).forEach(function (field) {
    if (PRIVATE_FINANCE_FIELDS.indexOf(field) !== -1) errors.push("private_finance_field:" + field);
  });
  return errors;
}

function validateRecord(record) {
  if (!isObject(record)) return ["invalid:record"];
  if (record.record_type === "BOT_RUNTIME") return validateBotRuntime(record);
  if (record.record_type === "RECOVERY_CERTIFICATION") return validateRecovery(record);
  if (record.record_type === "RELEASE_EVIDENCE") return validateReleaseEvidence(record);
  if (record.record_type === "RESEARCH_ENVELOPE") return validateResearchEnvelope(record);
  return ["invalid:record_type"];
}

module.exports = Object.freeze({
  validateRecord: validateRecord,
  validateBotRuntime: validateBotRuntime,
  validateRecovery: validateRecovery,
  validateReleaseEvidence: validateReleaseEvidence,
  validateResearchEnvelope: validateResearchEnvelope
});
