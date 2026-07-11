/**
 * AlphaMind OS — Atlas Learning Engine v0.1
 * Reads predictions and outcomes, compares results, drafts lessons,
 * and manages CEO approval workflow. Atlas (Chief Learning Officer).
 *
 * Uses confirmed live Supabase schema only (see LearningEngine.SCHEMA).
 *
 * v0.1 status workflow:
 *   proposed  — Atlas generates draft
 *   approved  — CEO approves
 *   rejected  — CEO rejects
 */

(function () {
  "use strict";

  function getSupabaseClient() {
    if (!window.supabaseClient) {
      throw new Error("Supabase client is not available.");
    }

    if (!window.LearningEngine) {
      throw new Error("LearningEngine helpers are not loaded.");
    }

    return window.supabaseClient;
  }

  function getSchema() {
    return window.LearningEngine.SCHEMA;
  }

  function getLessonStatus() {
    return window.LearningEngine.LESSON_STATUS;
  }

  /**
   * Load predictions, newest first.
   */
  async function loadPredictions(options) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();
    var settings = options || {};
    var query = supabaseClient
      .from(schema.predictions.table)
      .select(schema.predictions.columns)
      .order("created_at", { ascending: false });

    if (settings.limit) {
      query = query.limit(settings.limit);
    }

    var result = await query;

    if (result.error) {
      throw result.error;
    }

    return result.data || [];
  }

  /**
   * Load a single prediction by ID.
   */
  async function loadPredictionById(id) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();

    var result = await supabaseClient
      .from(schema.predictions.table)
      .select(schema.predictions.columns)
      .eq("id", id)
      .single();

    if (result.error) {
      throw result.error;
    }

    return result.data;
  }

  /**
   * Load the outcome linked to a prediction (v0.1: one outcome per prediction).
   */
  async function loadOutcomeByPredictionId(predictionId) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();

    var result = await supabaseClient
      .from(schema.outcomes.table)
      .select(schema.outcomes.columns)
      .eq("prediction_id", predictionId)
      .order("evaluated_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (result.error) {
      throw result.error;
    }

    return result.data;
  }

  /**
   * Load lessons filtered by status, newest first.
   */
  async function loadLessons(options) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();
    var settings = options || {};
    var query = supabaseClient
      .from(schema.lessons.table)
      .select(schema.lessons.columns)
      .order("created_at", { ascending: false });

    if (settings.status) {
      query = query.eq("status", settings.status);
    }

    if (settings.limit) {
      query = query.limit(settings.limit);
    }

    var result = await query;

    if (result.error) {
      throw result.error;
    }

    return result.data || [];
  }

  /**
   * Load a single lesson by ID.
   */
  async function loadLessonById(id) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();

    var result = await supabaseClient
      .from(schema.lessons.table)
      .select(schema.lessons.columns)
      .eq("id", id)
      .single();

    if (result.error) {
      throw result.error;
    }

    return result.data;
  }

  /**
   * Parse supporting_evidence jsonb values without LIKE/ILIKE.
   * Non-JSON strings return {} — do not use text-pattern matching on jsonb.
   */
  function parseSupportingEvidenceField(value) {
    if (value === null || value === undefined) {
      return {};
    }

    if (typeof value === "object") {
      return value;
    }

    if (typeof value === "string") {
      try {
        var parsedJson = JSON.parse(value);

        if (parsedJson && typeof parsedJson === "object" && !Array.isArray(parsedJson)) {
          return parsedJson;
        }
      } catch (parseError) {
        // Non-JSON string — not a queryable jsonb object.
      }

      return {};
    }

    return {};
  }

  function getEvidenceRecordId(evidence, key) {
    var raw = evidence[key];

    if (raw === null || raw === undefined || raw === "") {
      return null;
    }

    if (typeof raw === "number") {
      return Number.isFinite(raw) ? raw : null;
    }

    var number = Number(String(raw).trim());

    return Number.isFinite(number) ? number : null;
  }

  function toNumericOrNull(value) {
    if (value === null || value === undefined || value === "") {
      return null;
    }

    var number = Number(value);

    return Number.isFinite(number) ? number : null;
  }

  /**
   * Normalize draft evidence to a jsonb object for insert.
   * generateLessonDraft() currently produces a text string; this layer
   * ensures source_prediction_id and source_outcome_id are stored as jsonb keys.
   */
  function buildSupportingEvidenceJson(draft, predictionId, outcomeId, outcome) {
    var base = {
      source_prediction_id: Number(predictionId),
      source_outcome_id: Number(outcomeId)
    };
    var existing = draft.supporting_evidence;

    if (existing && typeof existing === "object" && !Array.isArray(existing)) {
      return Object.assign({}, existing, base);
    }

    if (typeof existing === "string" && existing) {
      base.traceability = existing;
    }

    if (outcome) {
      var confidenceError = toNumericOrNull(outcome.confidence_error);

      if (confidenceError !== null) {
        base.confidence_error = confidenceError;
      }
    }

    return base;
  }

  /**
   * Check whether a lesson already exists for a prediction–outcome pair.
   * Reads source IDs from supporting_evidence (jsonb) in application code.
   * Does not use LIKE/ILIKE against the jsonb column.
   */
  async function lessonExistsForPair(predictionId, outcomeId) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();
    var status = getLessonStatus();
    var targetPredictionId = Number(predictionId);
    var targetOutcomeId = Number(outcomeId);

    var result = await supabaseClient
      .from(schema.lessons.table)
      .select("id, supporting_evidence, status")
      .neq("status", status.REJECTED);

    if (result.error) {
      throw result.error;
    }

    var lessons = result.data || [];

    return lessons.some(function (lesson) {
      var evidence = parseSupportingEvidenceField(lesson.supporting_evidence);
      var lessonPredictionId = getEvidenceRecordId(evidence, "source_prediction_id");
      var lessonOutcomeId = getEvidenceRecordId(evidence, "source_outcome_id");

      return (
        lessonPredictionId === targetPredictionId &&
        lessonOutcomeId === targetOutcomeId
      );
    });
  }

  /**
   * Insert a draft lesson with proposed status.
   */
  async function saveLessonDraft(draft, predictionId, outcomeId, outcome) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();

    var exists = await lessonExistsForPair(predictionId, outcomeId);

    if (exists) {
      throw new Error("A lesson already exists for this prediction and outcome.");
    }

    var insertResult = await supabaseClient
      .from(schema.lessons.table)
      .insert([
        {
          title: draft.title,
          category: draft.category,
          lesson: draft.lesson,
          supporting_evidence: buildSupportingEvidenceJson(
            draft,
            predictionId,
            outcomeId,
            outcome
          ),
          sample_size: 1,
          measured_improvement: null,
          status: draft.status,
          created_by: draft.created_by
        }
      ])
      .select(schema.lessons.columns)
      .single();

    if (insertResult.error) {
      throw insertResult.error;
    }

    return insertResult.data;
  }

  /**
   * CEO approves a proposed lesson — proposed -> approved, sets reviewed_at.
   */
  async function approveLesson(id) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();
    var status = getLessonStatus();
    var lesson = await loadLessonById(id);

    if (lesson.status !== status.PROPOSED) {
      throw new Error("Only proposed lessons can be approved.");
    }

    var updateResult = await supabaseClient
      .from(schema.lessons.table)
      .update({
        status: status.APPROVED,
        reviewed_at: new Date().toISOString()
      })
      .eq("id", id)
      .eq("status", status.PROPOSED)
      .select(schema.lessons.columns)
      .single();

    if (updateResult.error) {
      throw updateResult.error;
    }

    return updateResult.data;
  }

  /**
   * CEO rejects a proposed lesson — proposed -> rejected, never deleted.
   */
  async function rejectLesson(id) {
    var supabaseClient = getSupabaseClient();
    var schema = getSchema();
    var status = getLessonStatus();
    var lesson = await loadLessonById(id);

    if (lesson.status !== status.PROPOSED) {
      throw new Error("Only proposed lessons can be rejected.");
    }

    var updateResult = await supabaseClient
      .from(schema.lessons.table)
      .update({ status: status.REJECTED })
      .eq("id", id)
      .eq("status", status.PROPOSED)
      .select(schema.lessons.columns)
      .single();

    if (updateResult.error) {
      throw updateResult.error;
    }

    return updateResult.data;
  }

  /**
   * Load predictions that have a recorded outcome (ready for lesson generation).
   */
  async function loadPredictionsWithOutcomes() {
    var predictions = await loadPredictions();
    var pairs = [];

    for (var i = 0; i < predictions.length; i += 1) {
      var prediction = predictions[i];
      var outcome = await loadOutcomeByPredictionId(prediction.id);

      if (outcome) {
        pairs.push({
          prediction: prediction,
          outcome: outcome
        });
      }
    }

    return pairs;
  }

  /**
   * Manual workflow: compare, draft, and save one lesson for a prediction.
   */
  async function generateAndSaveLesson(predictionId) {
    var prediction = await loadPredictionById(predictionId);
    var outcome = await loadOutcomeByPredictionId(predictionId);

    if (!outcome) {
      throw new Error("No outcome recorded for this prediction.");
    }

    if (!prediction.prediction_direction || !outcome.actual_direction) {
      throw new Error("Prediction direction and actual direction are required.");
    }

    var draft = window.LearningEngine.generateLessonDraft(prediction, outcome);

    return saveLessonDraft(draft, prediction.id, outcome.id, outcome);
  }

  window.AtlasLearningEngine = {
    loadPredictions: loadPredictions,
    loadPredictionById: loadPredictionById,
    loadOutcomeByPredictionId: loadOutcomeByPredictionId,
    loadLessons: loadLessons,
    loadLessonById: loadLessonById,
    lessonExistsForPair: lessonExistsForPair,
    saveLessonDraft: saveLessonDraft,
    approveLesson: approveLesson,
    rejectLesson: rejectLesson,
    loadPredictionsWithOutcomes: loadPredictionsWithOutcomes,
    generateAndSaveLesson: generateAndSaveLesson
  };
})();
