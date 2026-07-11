/**
 * AlphaMind OS — Learning page UI
 * Wires Atlas Learning Engine v0.1 to the Learning page.
 *
 * v0.1 status workflow:
 *   proposed  — awaiting CEO review
 *   approved  — CEO approved
 *   rejected  — CEO rejected
 */

var learningPageState = {
  pairs: [],
  proposedLessons: [],
  approvedLessons: [],
  predictionsById: {},
  outcomesByPredictionId: {},
  isGenerating: false,
  isReviewing: false
};

function parseLegacySupportingEvidenceText(text) {
  var parsed = {};

  text.split("\n").forEach(function (line) {
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

function normalizeSupportingEvidenceObject(value) {
  var evidence = Object.assign({}, value);

  if (typeof evidence.traceability === "string") {
    var fromTraceability = parseLegacySupportingEvidenceText(evidence.traceability);

    Object.keys(fromTraceability).forEach(function (key) {
      if (
        evidence[key] === undefined ||
        evidence[key] === null ||
        evidence[key] === ""
      ) {
        evidence[key] = fromTraceability[key];
      }
    });
  }

  return evidence;
}

function parseSupportingEvidence(value) {
  if (value === null || value === undefined) {
    return {};
  }

  if (typeof value === "object" && !Array.isArray(value)) {
    return normalizeSupportingEvidenceObject(value);
  }

  if (typeof value === "string") {
    try {
      var parsedJson = JSON.parse(value);

      if (parsedJson && typeof parsedJson === "object" && !Array.isArray(parsedJson)) {
        return normalizeSupportingEvidenceObject(parsedJson);
      }
    } catch (parseError) {
      // Legacy plain-text traceability format.
    }

    return parseLegacySupportingEvidenceText(value);
  }

  return {};
}

function formatSupportingEvidenceDisplay(value) {
  var evidence = parseSupportingEvidence(value);

  if (typeof evidence.traceability === "string" && evidence.traceability) {
    return evidence.traceability;
  }

  return JSON.stringify(evidence, null, 2);
}

document.addEventListener("DOMContentLoaded", function () {
  displayCurrentDate();
  setupGenerateLessonForm();
  setupPredictionSelect();
  loadLearningPage();
});

function displayCurrentDate() {
  var dateElement = document.getElementById("current-date");

  if (!dateElement) {
    return;
  }

  var today = new Date();
  var options = {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric"
  };

  dateElement.textContent = today.toLocaleDateString("en-US", options);
}

function setupGenerateLessonForm() {
  var form = document.getElementById("generate-lesson-form");

  if (!form) {
    return;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    await handleGenerateLesson(form);
  });
}

function setupPredictionSelect() {
  var select = document.getElementById("prediction-select");

  if (!select) {
    return;
  }

  select.addEventListener("change", function () {
    renderSelectedPairPreview(select.value);
  });
}

async function loadLearningPage() {
  if (!window.AtlasLearningEngine || !window.LearningEngine) {
    showLearningError(
      "Learning engine not loaded",
      "Check that learning-engine.js and atlas-learning-engine.js are included."
    );
    return;
  }

  setListLoading("pending-lessons-list", "Loading proposed lessons...");
  setListLoading("active-lessons-list", "Loading approved lessons...");

  try {
    var pairs = await AtlasLearningEngine.loadPredictionsWithOutcomes();
    var proposedLessons = await AtlasLearningEngine.loadLessons({
      status: LearningEngine.LESSON_STATUS.PROPOSED
    });
    var approvedLessons = await AtlasLearningEngine.loadLessons({
      status: LearningEngine.LESSON_STATUS.APPROVED
    });

    learningPageState.pairs = pairs;
    learningPageState.proposedLessons = proposedLessons;
    learningPageState.approvedLessons = approvedLessons;
    learningPageState.predictionsById = {};
    learningPageState.outcomesByPredictionId = {};

    pairs.forEach(function (pair) {
      learningPageState.predictionsById[pair.prediction.id] = pair.prediction;
      learningPageState.outcomesByPredictionId[pair.prediction.id] = pair.outcome;
    });

    await enrichLessonsWithContext(proposedLessons);
    await enrichLessonsWithContext(approvedLessons);

    renderPredictionSelect(pairs);
    renderProposedLessons(proposedLessons);
    renderApprovedLessons(approvedLessons);
  } catch (error) {
    console.error("Failed to load learning page:", error);
    showToast(getErrorMessage(error, "Could not load learning data. Check Supabase settings."));
    renderPredictionSelect([]);
    renderProposedLessons([]);
    renderApprovedLessons([]);
  }
}

async function enrichLessonsWithContext(lessons) {
  for (var i = 0; i < lessons.length; i += 1) {
    var lesson = lessons[i];
    var evidence = parseSupportingEvidence(lesson.supporting_evidence);
    var predictionId = evidence.source_prediction_id
      ? Number(evidence.source_prediction_id)
      : null;
    var outcomeId = evidence.source_outcome_id
      ? Number(evidence.source_outcome_id)
      : null;

    if (predictionId && !learningPageState.predictionsById[predictionId]) {
      try {
        learningPageState.predictionsById[predictionId] =
          await AtlasLearningEngine.loadPredictionById(predictionId);
      } catch (error) {
        console.error("Failed to load prediction for lesson:", error);
      }
    }

    if (predictionId && !learningPageState.outcomesByPredictionId[predictionId]) {
      try {
        var outcome = await AtlasLearningEngine.loadOutcomeByPredictionId(predictionId);

        if (outcome && (!outcomeId || outcome.id === outcomeId)) {
          learningPageState.outcomesByPredictionId[predictionId] = outcome;
        }
      } catch (error) {
        console.error("Failed to load outcome for lesson:", error);
      }
    }
  }
}

function renderPredictionSelect(pairs) {
  var select = document.getElementById("prediction-select");

  if (!select) {
    return;
  }

  select.innerHTML = "";

  if (pairs.length === 0) {
    select.innerHTML = '<option value="">No predictions with outcomes yet</option>';
    select.disabled = true;
    hideSelectedPairPreview();
    return;
  }

  select.disabled = false;

  var placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select a prediction...";
  select.appendChild(placeholder);

  pairs.forEach(function (pair) {
    var option = document.createElement("option");
    option.value = String(pair.prediction.id);
    option.textContent =
      LearningEngine.buildPredictionLabel(pair.prediction) +
      " · " +
      (pair.prediction.agent_role || "Learning");
    select.appendChild(option);
  });
}

function renderSelectedPairPreview(predictionId) {
  var preview = document.getElementById("selected-pair-preview");

  if (!preview) {
    return;
  }

  if (!predictionId) {
    hideSelectedPairPreview();
    return;
  }

  var prediction = learningPageState.predictionsById[predictionId];
  var outcome = learningPageState.outcomesByPredictionId[predictionId];

  if (!prediction || !outcome) {
    hideSelectedPairPreview();
    return;
  }

  preview.hidden = false;
  preview.innerHTML = buildOutcomePairHtml(prediction, outcome);
}

function hideSelectedPairPreview() {
  var preview = document.getElementById("selected-pair-preview");

  if (preview) {
    preview.hidden = true;
    preview.innerHTML = "";
  }
}

async function handleGenerateLesson(form) {
  if (learningPageState.isGenerating) {
    return;
  }

  var select = document.getElementById("prediction-select");
  var button = document.getElementById("btn-generate-lesson");
  var predictionId = select ? select.value : "";

  if (!predictionId) {
    showToast("Select a prediction with an outcome first.");
    return;
  }

  learningPageState.isGenerating = true;

  try {
    if (button) {
      button.disabled = true;
      button.textContent = "Generating...";
    }

    await AtlasLearningEngine.generateAndSaveLesson(Number(predictionId));
    showToast("Proposed lesson saved for CEO review.");
    await loadLearningPage();
  } catch (error) {
    console.error("Failed to generate lesson:", error);
    showToast(getErrorMessage(error, "Could not generate lesson."));
  } finally {
    learningPageState.isGenerating = false;

    if (button) {
      button.disabled = false;
      button.textContent = "Generate Draft Lesson";
    }
  }
}

function renderProposedLessons(lessons) {
  var container = document.getElementById("pending-lessons-list");
  var meta = document.getElementById("pending-meta");

  if (!container) {
    return;
  }

  container.innerHTML = "";

  if (meta) {
    meta.textContent =
      lessons.length === 0
        ? "No proposed lessons awaiting review."
        : lessons.length +
          (lessons.length === 1
            ? " proposed lesson awaiting approval."
            : " proposed lessons awaiting approval.");
  }

  if (lessons.length === 0) {
    container.innerHTML = getEmptyStateHtml(
      "No proposed lessons",
      "Generate a draft lesson from a prediction and outcome pair."
    );
    return;
  }

  lessons.forEach(function (lesson) {
    container.appendChild(createLessonCard(lesson, { showApprovalActions: true }));
  });
}

function renderApprovedLessons(lessons) {
  var container = document.getElementById("active-lessons-list");
  var meta = document.getElementById("active-meta");

  if (!container) {
    return;
  }

  container.innerHTML = "";

  if (meta) {
    meta.textContent =
      lessons.length === 0
        ? "No approved lessons yet."
        : lessons.length +
          (lessons.length === 1 ? " approved lesson." : " approved lessons.");
  }

  if (lessons.length === 0) {
    container.innerHTML = getEmptyStateHtml(
      "No approved lessons",
      "Approved lessons will appear here for future reference."
    );
    return;
  }

  lessons.forEach(function (lesson) {
    container.appendChild(createLessonCard(lesson, { showApprovalActions: false }));
  });
}

function createLessonCard(lesson, options) {
  var settings = options || {};
  var card = document.createElement("article");
  card.className = "learning-item";

  var evidence = parseSupportingEvidence(lesson.supporting_evidence);
  var predictionId = evidence.source_prediction_id
    ? Number(evidence.source_prediction_id)
    : null;
  var prediction = predictionId ? learningPageState.predictionsById[predictionId] : null;
  var outcome = predictionId ? learningPageState.outcomesByPredictionId[predictionId] : null;
  var comparisonResult = evidence.comparison || "unknown";
  var comparisonClass = "learning-item__comparison learning-item__comparison--" + comparisonResult;
  var comparisonLabel = LearningEngine.formatComparisonLabel(comparisonResult);

  card.innerHTML =
    '<div class="learning-item__header">' +
      '<div>' +
        '<h3 class="learning-item__title">' + escapeHtml(lesson.title || "Untitled lesson") + '</h3>' +
        '<p class="learning-item__meta">' +
          escapeHtml(lesson.category || "Learning") +
          " · " +
          formatLessonDate(lesson.created_at) +
        '</p>' +
      '</div>' +
      '<span class="' + comparisonClass + '">' + escapeHtml(comparisonLabel) + '</span>' +
    '</div>' +
    buildOutcomePairHtml(prediction, outcome) +
    buildLessonFieldsHtml(lesson) +
    (lesson.status === LearningEngine.LESSON_STATUS.APPROVED
      ? '<p class="learning-item__meta">Reviewed · ' + formatLessonDate(lesson.reviewed_at) + "</p>"
      : '<span class="learning-item__badge learning-item__badge--draft">Atlas Draft (Rule-Based)</span>');

  if (settings.showApprovalActions) {
    var actions = document.createElement("div");
    actions.className = "learning-item__actions";

    var approveButton = document.createElement("button");
    approveButton.type = "button";
    approveButton.className = "btn btn--primary";
    approveButton.textContent = "Approve";
    approveButton.addEventListener("click", function () {
      handleApproveLesson(lesson.id, approveButton);
    });

    var rejectButton = document.createElement("button");
    rejectButton.type = "button";
    rejectButton.className = "btn btn--secondary";
    rejectButton.textContent = "Reject";
    rejectButton.addEventListener("click", function () {
      handleRejectLesson(lesson.id, rejectButton);
    });

    actions.appendChild(approveButton);
    actions.appendChild(rejectButton);
    card.appendChild(actions);
  }

  return card;
}

function buildOutcomePairHtml(prediction, outcome) {
  if (!prediction || !outcome) {
    return "";
  }

  return (
    '<div class="learning-outcome-pair">' +
      '<div class="learning-outcome-pair__row">' +
        '<span class="learning-outcome-pair__label">Predicted</span>' +
        '<span class="learning-outcome-pair__value">' +
          escapeHtml(prediction.prediction_direction || "n/a") +
          " · " +
          escapeHtml(LearningEngine.formatPercent(prediction.predicted_change_percent)) +
          (prediction.confidence_score !== null && prediction.confidence_score !== undefined
            ? " · confidence " + escapeHtml(String(prediction.confidence_score))
            : "") +
        '</span>' +
      '</div>' +
      '<div class="learning-outcome-pair__row">' +
        '<span class="learning-outcome-pair__label">Actual</span>' +
        '<span class="learning-outcome-pair__value">' +
          escapeHtml(outcome.actual_direction || "n/a") +
          " · " +
          escapeHtml(LearningEngine.formatPercent(outcome.actual_change_percent)) +
          (outcome.direction_correct !== null && outcome.direction_correct !== undefined
            ? " · direction correct: " + escapeHtml(String(outcome.direction_correct))
            : "") +
        '</span>' +
      '</div>' +
      (outcome.evaluation_notes
        ? '<div class="learning-outcome-pair__row">' +
            '<span class="learning-outcome-pair__label">Notes</span>' +
            '<span class="learning-outcome-pair__value">' + escapeHtml(outcome.evaluation_notes) + '</span>' +
          '</div>'
        : "") +
    '</div>'
  );
}

function buildLessonFieldsHtml(lesson) {
  var fields = [
    { label: "Lesson", value: lesson.lesson },
    { label: "Measured improvement", value: lesson.measured_improvement },
    {
      label: "Supporting evidence",
      value: formatSupportingEvidenceDisplay(lesson.supporting_evidence)
    }
  ];

  return fields
    .map(function (field) {
      return (
        '<div class="learning-field">' +
          '<span class="learning-field__label">' + escapeHtml(field.label) + '</span>' +
          '<p class="learning-field__value">' + escapeHtml(field.value || "—") + '</p>' +
        '</div>'
      );
    })
    .join("");
}

async function handleApproveLesson(lessonId, button) {
  if (learningPageState.isReviewing) {
    return;
  }

  learningPageState.isReviewing = true;

  try {
    if (button) {
      button.disabled = true;
      button.textContent = "Approving...";
    }

    await AtlasLearningEngine.approveLesson(lessonId);
    showToast("Lesson approved.");
    await loadLearningPage();
  } catch (error) {
    console.error("Failed to approve lesson:", error);
    showToast(getErrorMessage(error, "Could not approve lesson."));

    if (button) {
      button.disabled = false;
      button.textContent = "Approve";
    }
  } finally {
    learningPageState.isReviewing = false;
  }
}

async function handleRejectLesson(lessonId, button) {
  if (learningPageState.isReviewing) {
    return;
  }

  learningPageState.isReviewing = true;

  try {
    if (button) {
      button.disabled = true;
      button.textContent = "Rejecting...";
    }

    await AtlasLearningEngine.rejectLesson(lessonId);
    showToast("Lesson rejected and archived.");
    await loadLearningPage();
  } catch (error) {
    console.error("Failed to reject lesson:", error);
    showToast(getErrorMessage(error, "Could not reject lesson."));

    if (button) {
      button.disabled = false;
      button.textContent = "Reject";
    }
  } finally {
    learningPageState.isReviewing = false;
  }
}

function setListLoading(containerId, message) {
  var container = document.getElementById(containerId);

  if (container) {
    container.innerHTML = getEmptyStateHtml("Loading...", message);
  }
}

function showLearningError(title, text) {
  var proposed = document.getElementById("pending-lessons-list");
  var approved = document.getElementById("active-lessons-list");

  if (proposed) {
    proposed.innerHTML = getEmptyStateHtml(title, text);
  }

  if (approved) {
    approved.innerHTML = getEmptyStateHtml(title, text);
  }
}

function getEmptyStateHtml(title, text) {
  return (
    '<div class="empty-state">' +
      '<p class="empty-state__title">' + escapeHtml(title) + '</p>' +
      '<p class="empty-state__text">' + escapeHtml(text) + '</p>' +
    '</div>'
  );
}

function formatLessonDate(isoString) {
  if (!isoString) {
    return "";
  }

  var date = new Date(isoString);

  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function getErrorMessage(error, fallback) {
  if (error && error.message) {
    return error.message;
  }

  return fallback;
}

function escapeHtml(text) {
  var div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function showToast(message) {
  var toast = document.getElementById("toast");

  if (!toast) {
    return;
  }

  toast.textContent = message;
  toast.hidden = false;
  toast.style.opacity = "1";

  if (toast.hideTimer) {
    clearTimeout(toast.hideTimer);
  }

  toast.hideTimer = setTimeout(function () {
    toast.style.opacity = "0";

    setTimeout(function () {
      toast.hidden = true;
    }, 250);
  }, 3000);
}
