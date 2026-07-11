/**
 * AlphaMind OS — Learning Engine helpers
 * Rule-based comparison and lesson draft generation for Atlas v0.1.
 *
 * Pure functions only — no Supabase I/O.
 * Schema: confirmed live Supabase columns only (see SCHEMA).
 */

(function () {
  "use strict";

  var PERCENT_MATCH_TOLERANCE = 0.5;
  var PERCENT_PARTIAL_TOLERANCE = 2.0;
  var DEFAULT_CREATED_BY = "Atlas";

  var SCHEMA = {
    predictions: {
      table: "ai_predictions",
      columns:
        "id, observation_id, model_name, agent_role, prediction_direction, confidence_score, prediction_horizon, predicted_change_percent, evidence, risks, assumptions, reasoning, invalidation_condition, created_at"
    },
    outcomes: {
      table: "prediction_outcomes",
      columns:
        "id, prediction_id, evaluated_at, actual_direction, actual_change_percent, outcome_price, direction_correct, confidence_error, evaluation_notes, created_at"
    },
    lessons: {
      table: "learning_lessons",
      columns:
        "id, title, category, lesson, supporting_evidence, sample_size, measured_improvement, status, created_by, created_at, reviewed_at"
    }
  };

  var COMPARISON_RESULTS = {
    MATCH: "match",
    PARTIAL: "partial_match",
    MISMATCH: "mismatch"
  };

  /**
   * Confirmed live learning_lessons.status values.
   * v0.1 workflow uses PROPOSED, APPROVED, REJECTED only.
   */
  var LESSON_STATUS = {
    PROPOSED: "proposed",
    BACKTESTING: "backtesting",
    PAPER_TESTING: "paper_testing",
    APPROVED: "approved",
    REJECTED: "rejected",
    RETIRED: "retired"
  };

  function normalizeDirection(value) {
    var direction = (value || "").toLowerCase().trim();

    if (
      direction === "up" ||
      direction === "bull" ||
      direction === "bullish" ||
      direction === "long" ||
      direction === "positive"
    ) {
      return "up";
    }

    if (
      direction === "down" ||
      direction === "bear" ||
      direction === "bearish" ||
      direction === "short" ||
      direction === "negative"
    ) {
      return "down";
    }

    if (
      direction === "flat" ||
      direction === "neutral" ||
      direction === "sideways" ||
      direction === "unchanged"
    ) {
      return "flat";
    }

    return direction;
  }

  function toNumber(value) {
    if (value === null || value === undefined || value === "") {
      return null;
    }

    var number = Number(value);

    return Number.isFinite(number) ? number : null;
  }

  function formatPercent(value) {
    var number = toNumber(value);

    if (number === null) {
      return "n/a";
    }

    return number + "%";
  }

  function comparePercentChange(predicted, actual) {
    var predictedNumber = toNumber(predicted);
    var actualNumber = toNumber(actual);

    if (predictedNumber === null || actualNumber === null) {
      return null;
    }

    var difference = Math.abs(predictedNumber - actualNumber);

    if (difference <= PERCENT_MATCH_TOLERANCE) {
      return COMPARISON_RESULTS.MATCH;
    }

    if (difference <= PERCENT_PARTIAL_TOLERANCE) {
      return COMPARISON_RESULTS.PARTIAL;
    }

    return COMPARISON_RESULTS.MISMATCH;
  }

  function comparePredictionPair(prediction, outcome) {
    if (!prediction || !outcome) {
      throw new Error("Prediction and outcome are required for comparison.");
    }

    if (!prediction.prediction_direction || !outcome.actual_direction) {
      throw new Error("Prediction direction and actual direction are required.");
    }

    if (outcome.direction_correct === true) {
      var percentWhenCorrect = comparePercentChange(
        prediction.predicted_change_percent,
        outcome.actual_change_percent
      );

      if (percentWhenCorrect === COMPARISON_RESULTS.MISMATCH) {
        return COMPARISON_RESULTS.PARTIAL;
      }

      return COMPARISON_RESULTS.MATCH;
    }

    if (outcome.direction_correct === false) {
      return COMPARISON_RESULTS.MISMATCH;
    }

    var predictedDirection = normalizeDirection(prediction.prediction_direction);
    var actualDirection = normalizeDirection(outcome.actual_direction);

    if (predictedDirection !== actualDirection) {
      return COMPARISON_RESULTS.MISMATCH;
    }

    var percentResult = comparePercentChange(
      prediction.predicted_change_percent,
      outcome.actual_change_percent
    );

    if (percentResult === COMPARISON_RESULTS.MATCH || percentResult === null) {
      return COMPARISON_RESULTS.MATCH;
    }

    if (percentResult === COMPARISON_RESULTS.PARTIAL) {
      return COMPARISON_RESULTS.PARTIAL;
    }

    return COMPARISON_RESULTS.MISMATCH;
  }

  function formatComparisonLabel(comparison) {
    var labels = {
      match: "Match",
      partial_match: "Partial match",
      mismatch: "Mismatch"
    };

    return labels[comparison] || comparison;
  }

  function buildPredictionLabel(prediction) {
    var parts = [];

    if (prediction.model_name) {
      parts.push(prediction.model_name);
    }

    if (prediction.prediction_direction) {
      parts.push(String(prediction.prediction_direction).toUpperCase());
    }

    if (prediction.predicted_change_percent !== null && prediction.predicted_change_percent !== undefined) {
      parts.push(formatPercent(prediction.predicted_change_percent));
    }

    if (parts.length === 0) {
      return "Prediction #" + prediction.id;
    }

    return parts.join(" · ");
  }

  function buildMeasuredImprovement(prediction, outcome) {
    var predicted = toNumber(prediction.predicted_change_percent);
    var actual = toNumber(outcome.actual_change_percent);

    if (predicted === null || actual === null) {
      if (outcome.confidence_error !== null && outcome.confidence_error !== undefined) {
        return "Confidence error: " + outcome.confidence_error;
      }

      return "Direction evaluated only";
    }

    var delta = actual - predicted;
    var sign = delta >= 0 ? "+" : "";

    return (
      "Predicted " +
      formatPercent(predicted) +
      ", actual " +
      formatPercent(actual) +
      " (" +
      sign +
      delta.toFixed(2) +
      " pp delta)"
    );
  }

  function buildLessonBody(prediction, outcome, comparison) {
    var label = buildPredictionLabel(prediction);
    var notes = outcome.evaluation_notes || "";
    var worked = "";
    var failed = "";
    var causes = "";
    var recommendation = "";

    if (comparison === COMPARISON_RESULTS.MATCH) {
      worked =
        label +
        " aligned with the observed outcome. Direction: " +
        prediction.prediction_direction +
        " vs " +
        outcome.actual_direction +
        ". Change: predicted " +
        formatPercent(prediction.predicted_change_percent) +
        ", actual " +
        formatPercent(outcome.actual_change_percent) +
        ".";
      failed = "Nothing significant failed in this evaluation.";
      causes =
        "Model " +
        (prediction.model_name || "unknown") +
        " assumptions held. Agent role: " +
        (prediction.agent_role || "n/a") +
        ". Horizon: " +
        (prediction.prediction_horizon || "n/a") +
        ".";
      recommendation =
        "Continue using this prediction pattern for similar observations. Confidence score was " +
        (prediction.confidence_score !== null && prediction.confidence_score !== undefined
          ? prediction.confidence_score
          : "n/a") +
        ".";
    } else if (comparison === COMPARISON_RESULTS.PARTIAL) {
      worked =
        "Direction matched (" +
        prediction.prediction_direction +
        " vs " +
        outcome.actual_direction +
        ") but magnitude differed. Predicted " +
        formatPercent(prediction.predicted_change_percent) +
        ", actual " +
        formatPercent(outcome.actual_change_percent) +
        ".";
      failed = "Predicted change percent did not fully match the observed move.";
      causes =
        "Timing, horizon (" +
        (prediction.prediction_horizon || "n/a") +
        "), or volatility may explain the gap." +
        (notes ? " Evaluation notes: " + notes : "");
      recommendation =
        "Tighten magnitude thresholds and review invalidation condition: " +
        (prediction.invalidation_condition || "not specified") +
        ".";
    } else {
      worked =
        outcome.direction_correct === false
          ? "Outcome was evaluated and direction_correct was marked false."
          : "Evaluation captured a clear miss for learning purposes.";
      failed =
        label +
        " missed. Predicted " +
        prediction.prediction_direction +
        " (" +
        formatPercent(prediction.predicted_change_percent) +
        "), actual " +
        outcome.actual_direction +
        " (" +
        formatPercent(outcome.actual_change_percent) +
        ").";
      causes =
        "Review reasoning, assumptions, and risks from the original prediction." +
        (prediction.risks ? " Risks noted: " + prediction.risks : "") +
        (notes ? " Evaluation notes: " + notes : "");
      recommendation =
        "Require stronger evidence before similar " +
        (prediction.agent_role || "agent") +
        " predictions. Re-check assumptions: " +
        (prediction.assumptions || "none recorded") +
        ".";
    }

    return (
      "Atlas Draft (Rule-Based)\n\n" +
      "Comparison: " +
      formatComparisonLabel(comparison) +
      "\n\n" +
      "What worked\n" +
      worked +
      "\n\n" +
      "What failed\n" +
      failed +
      "\n\n" +
      "Likely causes\n" +
      causes +
      "\n\n" +
      "Future recommendation\n" +
      recommendation
    );
  }

  function buildSupportingEvidence(prediction, outcome, comparison) {
    return (
      "source_prediction_id: " +
      prediction.id +
      "\n" +
      "source_outcome_id: " +
      outcome.id +
      "\n" +
      "observation_id: " +
      (prediction.observation_id || "n/a") +
      "\n" +
      "comparison: " +
      comparison +
      "\n" +
      "model_name: " +
      (prediction.model_name || "n/a") +
      "\n" +
      "prediction_direction: " +
      (prediction.prediction_direction || "n/a") +
      "\n" +
      "actual_direction: " +
      (outcome.actual_direction || "n/a") +
      "\n" +
      "predicted_change_percent: " +
      formatPercent(prediction.predicted_change_percent) +
      "\n" +
      "actual_change_percent: " +
      formatPercent(outcome.actual_change_percent) +
      "\n" +
      "direction_correct: " +
      (outcome.direction_correct === null || outcome.direction_correct === undefined
        ? "n/a"
        : outcome.direction_correct) +
      "\n" +
      "confidence_error: " +
      (outcome.confidence_error !== null && outcome.confidence_error !== undefined
        ? outcome.confidence_error
        : "n/a") +
      "\n" +
      "evidence: " +
      (prediction.evidence || "n/a") +
      "\n" +
      "evaluation_notes: " +
      (outcome.evaluation_notes || "n/a")
    );
  }

  function parseSupportingEvidence(text) {
    var parsed = {};

    (text || "").split("\n").forEach(function (line) {
      var separatorIndex = line.indexOf(":");

      if (separatorIndex === -1) {
        return;
      }

      var key = line.slice(0, separatorIndex).trim();
      var value = line.slice(separatorIndex + 1).trim();
      parsed[key] = value;
    });

    return parsed;
  }

  /**
   * Build a draft lesson mapped only to learning_lessons write columns.
   * New lessons always start as proposed.
   */
  function generateLessonDraft(prediction, outcome) {
    var comparison = comparePredictionPair(prediction, outcome);
    var improvementNote = buildMeasuredImprovement(prediction, outcome);

    return {
      title:
        "Lesson: " +
        buildPredictionLabel(prediction) +
        " (" +
        formatComparisonLabel(comparison) +
        ")",
      category: prediction.agent_role || "Learning",
      lesson:
        buildLessonBody(prediction, outcome, comparison) +
        "\n\nImprovement note\n" +
        improvementNote,
      supporting_evidence: buildSupportingEvidence(prediction, outcome, comparison),
      sample_size: 1,
      measured_improvement: null,
      status: LESSON_STATUS.PROPOSED,
      created_by: DEFAULT_CREATED_BY
    };
  }

  window.LearningEngine = {
    SCHEMA: SCHEMA,
    COMPARISON_RESULTS: COMPARISON_RESULTS,
    LESSON_STATUS: LESSON_STATUS,
    DEFAULT_CREATED_BY: DEFAULT_CREATED_BY,
    PERCENT_MATCH_TOLERANCE: PERCENT_MATCH_TOLERANCE,
    PERCENT_PARTIAL_TOLERANCE: PERCENT_PARTIAL_TOLERANCE,
    normalizeDirection: normalizeDirection,
    comparePercentChange: comparePercentChange,
    comparePredictionPair: comparePredictionPair,
    generateLessonDraft: generateLessonDraft,
    formatComparisonLabel: formatComparisonLabel,
    buildPredictionLabel: buildPredictionLabel,
    buildMeasuredImprovement: buildMeasuredImprovement,
    parseSupportingEvidence: parseSupportingEvidence,
    formatPercent: formatPercent
  };
})();
