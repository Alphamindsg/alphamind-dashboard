/**
 * AlphaMind CEO Command Center — Main application logic
 * Handles the Command Center, navigation, and existing Memory MVP workflows.
 */

var memoryPageState = {
  allMemories: [],
  activeCategory: "All",
  searchQuery: "",
  searchTimer: null
};

var memoryUiState = {
  editingId: null,
  activeMemory: null
};

var isSavingMemory = false;
var isQuickCapturing = false;

var COMMAND_CENTER_CONFIG = {
  focusTags: ["focus-1", "focus-2", "focus-3"],
  waitingTag: "waiting-ceo",
  progressTags: ["completed", "done"],
  waitingLimit: 5,
  recentKnowledgeLimit: 5,
  progressLimit: 5,
  quickCaptureCategory: "Learning",
  quickCaptureTag: "quick-capture",
  systemPulse: [
    { name: "Memory", status: "Healthy" },
    { name: "Engineering", status: "Healthy" },
    { name: "Research", status: "Learning" },
    { name: "Creator Studio", status: "Planning" }
  ]
};

var IMPORTANCE_CLASS_ALLOWLIST = ["low", "medium", "high", "critical"];

function normalizeImportanceClass(value) {
  var normalized = String(value || "").toLowerCase().trim();

  return IMPORTANCE_CLASS_ALLOWLIST.indexOf(normalized) !== -1 ? normalized : "medium";
}

document.addEventListener("DOMContentLoaded", function () {
  displayCurrentDateTime();
  window.setInterval(displayCurrentDateTime, 30000);
  setupSidebarNavigation();
  setupCommandCenterActions();
  setupMemoryModal();
  setupMemoryPage();
  setupMemoryDetailPanel();
  renderSystemPulse();
  loadCommandCenter();
});

function displayCurrentDateTime() {
  var dateElement = document.getElementById("current-date");
  var timeElement = document.getElementById("current-time");

  if (!dateElement && !timeElement) {
    return;
  }

  var today = new Date();
  var options = {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric"
  };

  if (dateElement) {
    dateElement.textContent = today.toLocaleDateString("en-US", options);
  }

  if (timeElement) {
    timeElement.textContent = today.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit"
    });
  }
}

function setupSidebarNavigation() {
  var sidebarLinks = document.querySelectorAll(".sidebar__link");

  sidebarLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      var navTarget = link.getAttribute("data-nav");

      if (navTarget === "dashboard") {
        setActiveSidebarLink(sidebarLinks, link);
        showPage("dashboard");
        loadCommandCenter();
        return;
      }

      if (navTarget === "memory") {
        setActiveSidebarLink(sidebarLinks, link);
        showPage("memory");
        loadMemoryPage();
        return;
      }
    });
  });
}

function setActiveSidebarLink(sidebarLinks, activeLink) {
  sidebarLinks.forEach(function (item) {
    item.classList.remove("sidebar__link--active");
  });

  activeLink.classList.add("sidebar__link--active");
}

function showPage(pageName) {
  var dashboardPage = document.getElementById("page-dashboard");
  var memoryPage = document.getElementById("page-memory");

  if (dashboardPage) {
    dashboardPage.hidden = pageName !== "dashboard";
  }

  if (memoryPage) {
    memoryPage.hidden = pageName !== "memory";
  }
}

function setupCommandCenterActions() {
  var quickCaptureForm = document.getElementById("quick-capture-form");
  var openMemoryButton = document.getElementById("btn-open-memory");
  var addMemoryPageButton = document.getElementById("btn-add-memory-page");

  if (addMemoryPageButton) {
    addMemoryPageButton.addEventListener("click", openCreateMemoryModal);
  }

  if (openMemoryButton) {
    openMemoryButton.addEventListener("click", navigateToMemory);
  }

  if (quickCaptureForm) {
    quickCaptureForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      await saveQuickCapture();
    });
  }
}

function navigateToMemory() {
  var sidebarLinks = document.querySelectorAll(".sidebar__link");
  var memoryLink = document.querySelector('.sidebar__link[data-nav="memory"]');

  if (memoryLink) {
    setActiveSidebarLink(sidebarLinks, memoryLink);
  }

  showPage("memory");
  loadMemoryPage();
}

function getNormalizedMemoryTags(memory) {
  if (window.MemoryEngine && typeof MemoryEngine.normalizeTags === "function") {
    return Array.from(MemoryEngine.normalizeTags((memory && memory.tags) || []));
  }

  return Array.isArray(memory && memory.tags)
    ? memory.tags.map(function (tag) {
        return String(tag || "").toLowerCase().trim();
      })
    : [];
}

function memoryHasTag(memory, tag) {
  return getNormalizedMemoryTags(memory).indexOf(tag) !== -1;
}

function getMemoryTime(memory) {
  var value = (memory && (memory.updated_at || memory.created_at)) || "";
  var time = Date.parse(value);

  return Number.isFinite(time) ? time : 0;
}

function sortByMemoryTimeDescending(memories) {
  return memories.slice().sort(function (left, right) {
    return getMemoryTime(right) - getMemoryTime(left);
  });
}

function selectFocusMemories(memories) {
  var selected = [];
  var usedIds = Object.create(null);

  COMMAND_CENTER_CONFIG.focusTags.forEach(function (focusTag, focusIndex) {
    var match = sortByMemoryTimeDescending(
      memories.filter(function (memory) {
        return !usedIds[memory.id] && memoryHasTag(memory, focusTag);
      })
    )[0];

    if (match) {
      selected.push(
        Object.assign({}, match, {
          command_center_focus_position: focusIndex + 1
        })
      );
      usedIds[match.id] = true;
    }
  });

  return selected.slice(0, 3);
}

function selectWaitingForCeoMemories(memories) {
  return sortByMemoryTimeDescending(
    memories.filter(function (memory) {
      return memoryHasTag(memory, COMMAND_CENTER_CONFIG.waitingTag);
    })
  ).slice(0, COMMAND_CENTER_CONFIG.waitingLimit);
}

function selectProgressMemories(memories) {
  return sortByMemoryTimeDescending(
    memories.filter(function (memory) {
      return COMMAND_CENTER_CONFIG.progressTags.some(function (tag) {
        return memoryHasTag(memory, tag);
      });
    })
  ).slice(0, COMMAND_CENTER_CONFIG.progressLimit);
}

function selectRecentKnowledge(memories, excludedMemories) {
  var excludedIds = Object.create(null);
  var importanceRank = { Critical: 4, High: 3, Medium: 2, Low: 1 };

  (excludedMemories || []).forEach(function (memory) {
    excludedIds[memory.id] = true;
  });

  return memories
    .filter(function (memory) {
      return !excludedIds[memory.id];
    })
    .sort(function (left, right) {
      var leftRank = importanceRank[left.importance] || 0;
      var rightRank = importanceRank[right.importance] || 0;

      if (leftRank !== rightRank) {
        return rightRank - leftRank;
      }

      return getMemoryTime(right) - getMemoryTime(left);
    })
    .slice(0, COMMAND_CENTER_CONFIG.recentKnowledgeLimit);
}

function getWaitingReason(memory) {
  var tags = getNormalizedMemoryTags(memory);
  var reasons = [
    { tag: "pr-approval", label: "PR approval" },
    { tag: "executive-decision", label: "Executive decision" },
    { tag: "review", label: "Review" },
    { tag: "outstanding-action", label: "Outstanding action" }
  ];
  var match = reasons.find(function (reason) {
    return tags.indexOf(reason.tag) !== -1;
  });

  return match ? match.label : "CEO attention";
}

function createQuickCaptureTitle(text) {
  var normalized = String(text || "").trim().replace(/\s+/g, " ");
  var firstSentence = normalized.split(/[.!?](?:\s|$)/)[0] || normalized;
  var title = firstSentence.slice(0, 72).trim();

  if (firstSentence.length > 72) {
    title = title.replace(/\s+\S*$/, "").trim() || firstSentence.slice(0, 72).trim();
  }

  return title || "Quick capture";
}

async function saveQuickCapture() {
  var input = document.getElementById("quick-capture-input");
  var button = document.getElementById("btn-quick-capture");
  var text = input ? input.value.trim() : "";

  if (!text || isQuickCapturing || !window.MemoryEngine) {
    return;
  }

  isQuickCapturing = true;

  try {
    if (button) {
      button.disabled = true;
      button.textContent = "Capturing...";
    }

    await MemoryEngine.saveMemory({
      title: createQuickCaptureTitle(text),
      category: COMMAND_CENTER_CONFIG.quickCaptureCategory,
      notes: text,
      tags: COMMAND_CENTER_CONFIG.quickCaptureTag,
      source: "command-center"
    });

    input.value = "";
    await loadCommandCenter();
    showToast("Knowledge captured");
    input.focus();
  } catch (error) {
    console.error("Failed to capture knowledge:", error);
    showToast("Could not capture knowledge. Check your Supabase settings.");
  } finally {
    isQuickCapturing = false;

    if (button) {
      button.disabled = false;
      button.textContent = "Capture";
    }
  }
}

async function loadCommandCenter() {
  var containerIds = [
    "today-focus-list",
    "waiting-ceo-list",
    "recent-knowledge-list",
    "today-progress-list"
  ];
  var containers = containerIds
    .map(function (id) {
      return document.getElementById(id);
    })
    .filter(Boolean);

  if (!containers.length) {
    return;
  }

  containers.forEach(function (container) {
    container.innerHTML = getLoadingStateHtml("Loading...", "Reading existing Memory records.");
  });

  if (!window.MemoryEngine) {
    containers.forEach(function (container) {
      container.innerHTML = getErrorStateHtml("Memory unavailable", "The existing Memory engine did not load.");
    });
    return;
  }

  try {
    var memories = await MemoryEngine.loadMemories({ limit: 200 });
    var focusMemories = selectFocusMemories(memories);
    var waitingMemories = selectWaitingForCeoMemories(memories);
    var progressMemories = selectProgressMemories(memories);
    var recentKnowledge = selectRecentKnowledge(
      memories,
      focusMemories.concat(waitingMemories, progressMemories)
    );

    renderCommandList("today-focus-list", focusMemories, {
      emptyTitle: "No focus items selected",
      emptyText: "Add focus-1, focus-2, or focus-3 to existing Memory records.",
      kind: "focus"
    });
    renderCommandList("waiting-ceo-list", waitingMemories, {
      emptyTitle: "Nothing is waiting",
      emptyText: "Existing records tagged waiting-ceo will appear here.",
      kind: "waiting"
    });
    renderCommandList("recent-knowledge-list", recentKnowledge, {
      emptyTitle: "No recent knowledge",
      emptyText: "Create or update a Memory record to see it here.",
      kind: "knowledge"
    });
    renderCommandList("today-progress-list", progressMemories, {
      emptyTitle: "No completed actions recorded",
      emptyText: "Existing records tagged completed or done will appear here.",
      kind: "progress"
    });
  } catch (error) {
    console.error("Failed to load CEO Command Center:", error);
    containers.forEach(function (container) {
      container.innerHTML = getErrorStateHtml(
        "Could not load Command Center data",
        "Check the existing Supabase URL, publishable key, and table permissions."
      );
    });
  }
}

function renderCommandList(containerId, memories, options) {
  var container = document.getElementById(containerId);
  var settings = options || {};

  if (!container) {
    return;
  }

  container.innerHTML = "";

  if (!memories.length) {
    container.innerHTML = getEmptyStateHtml(settings.emptyTitle, settings.emptyText);
    return;
  }

  memories.forEach(function (memory, index) {
    container.appendChild(createCommandItem(memory, settings.kind, index));
  });
}

function createCommandItem(memory, kind, index) {
  var button = document.createElement("button");
  var header = document.createElement("span");
  var badge = document.createElement("span");
  var title = document.createElement("span");
  var notes = document.createElement("span");
  var footer = document.createElement("span");
  var category = document.createElement("span");
  var importance = document.createElement("span");
  var date = document.createElement("span");

  button.type = "button";
  button.className = "command-item command-item--" + (kind || "knowledge");
  button.addEventListener("click", function () {
    openMemoryDetail(memory.id);
  });

  header.className = "command-item__header";
  badge.className = "command-item__badge";
  badge.textContent = getCommandItemBadge(memory, kind, index);
  title.className = "command-item__title";
  title.textContent = memory.title || "Untitled memory";
  header.appendChild(badge);
  header.appendChild(title);

  notes.className = "command-item__notes";
  notes.textContent = truncateText(memory.notes || "", 120);

  footer.className = "command-item__footer";
  category.className = "command-item__category";
  category.textContent = memory.category || "Uncategorized";
  importance.className =
    "command-item__importance command-item__importance--" +
    normalizeImportanceClass(memory.importance);
  importance.textContent = memory.importance || "Medium";
  date.className = "command-item__date";
  date.textContent = formatMemoryDate(memory.updated_at || memory.created_at);
  footer.appendChild(category);
  footer.appendChild(importance);
  footer.appendChild(date);

  button.appendChild(header);
  button.appendChild(notes);
  button.appendChild(footer);

  return button;
}

function getCommandItemBadge(memory, kind, index) {
  if (kind === "focus") {
    return String(memory.command_center_focus_position || index + 1);
  }

  if (kind === "waiting") {
    return getWaitingReason(memory);
  }

  if (kind === "progress") {
    return "Completed";
  }

  return "Knowledge";
}

function truncateText(text, maximumLength) {
  var normalized = String(text || "").trim().replace(/\s+/g, " ");

  if (normalized.length <= maximumLength) {
    return normalized;
  }

  return normalized.slice(0, maximumLength - 1).trimEnd() + "…";
}

function renderSystemPulse() {
  var container = document.getElementById("system-pulse-list");

  if (!container) {
    return;
  }

  container.innerHTML = "";

  COMMAND_CENTER_CONFIG.systemPulse.forEach(function (item) {
    var row = document.createElement("div");
    var name = document.createElement("span");
    var status = document.createElement("span");

    row.className = "pulse-item";
    name.className = "pulse-item__name";
    name.textContent = item.name;
    status.className = "pulse-item__status pulse-item__status--" + item.status.toLowerCase();
    status.textContent = item.status;
    row.appendChild(name);
    row.appendChild(status);
    container.appendChild(row);
  });
}

function setupMemoryModal() {
  var modal = document.getElementById("memory-modal");
  var form = document.getElementById("memory-form");
  var cancelButton = document.getElementById("btn-cancel-memory");

  if (!modal || !form) {
    return;
  }

  if (cancelButton) {
    cancelButton.addEventListener("click", closeMemoryModal);
  }

  modal.addEventListener("click", function (event) {
    if (event.target === modal) {
      closeMemoryModal();
    }
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    await saveMemoryFromForm(form);
  });
}

function setupMemoryPage() {
  var searchInput = document.getElementById("memory-search-input");
  var filtersContainer = document.getElementById("memory-category-filters");

  if (!searchInput || !filtersContainer || !window.MemoryEngine) {
    return;
  }

  MemoryEngine.CATEGORIES.forEach(function (category) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "memory-filter" + (category === "All" ? " memory-filter--active" : "");
    button.textContent = category;
    button.setAttribute("data-category", category);

    button.addEventListener("click", function () {
      memoryPageState.activeCategory = category;

      filtersContainer.querySelectorAll(".memory-filter").forEach(function (filterButton) {
        filterButton.classList.remove("memory-filter--active");
      });

      button.classList.add("memory-filter--active");
      renderMemorySearchResults();
    });

    filtersContainer.appendChild(button);
  });

  searchInput.addEventListener("input", function () {
    memoryPageState.searchQuery = searchInput.value;

    if (memoryPageState.searchTimer) {
      clearTimeout(memoryPageState.searchTimer);
    }

    memoryPageState.searchTimer = setTimeout(function () {
      renderMemorySearchResults();
    }, 300);
  });
}

function setupMemoryDetailPanel() {
  var overlay = document.getElementById("memory-detail-overlay");
  var closeButton = document.getElementById("memory-detail-close");
  var editButton = document.getElementById("btn-edit-memory");

  if (!overlay) {
    return;
  }

  if (closeButton) {
    closeButton.addEventListener("click", closeMemoryDetail);
  }

  if (editButton) {
    editButton.addEventListener("click", openEditMemoryModal);
  }

  overlay.addEventListener("click", function (event) {
    if (event.target === overlay) {
      closeMemoryDetail();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !overlay.hidden) {
      closeMemoryDetail();
    }
  });
}

function openCreateMemoryModal() {
  openMemoryModal(null);
}

function openEditMemoryModal() {
  var memory = memoryUiState.activeMemory;

  if (!memory) {
    return;
  }

  closeMemoryDetail();
  openMemoryModal(memory);
}

function openMemoryModal(memory) {
  var modal = document.getElementById("memory-modal");
  var form = document.getElementById("memory-form");
  var modalTitle = document.getElementById("modal-title");
  var modalSubtitle = document.getElementById("modal-subtitle");
  var titleInput = document.getElementById("memory-title");
  var categoryInput = document.getElementById("memory-category");
  var notesInput = document.getElementById("memory-notes");
  var tagsInput = document.getElementById("memory-tags");
  var saveButton = document.getElementById("btn-save-memory");

  if (!modal || !form) {
    return;
  }

  form.reset();
  memoryUiState.editingId = memory ? memory.id : null;

  if (memory) {
    modalTitle.textContent = "Edit Memory";
    modalSubtitle.textContent = "Update this memory and refresh its derived metadata.";
    saveButton.textContent = "Save Changes";
    titleInput.value = memory.title || "";
    categoryInput.value = memory.category || "";
    notesInput.value = memory.notes || "";
    tagsInput.value = formatTagsForInput(MemoryEngine.getManualTags(memory));
  } else {
    modalTitle.textContent = "Add Memory";
    modalSubtitle.textContent = "Save a note to the AlphaMind memory system.";
    saveButton.textContent = "Save";
  }

  modal.hidden = false;
  document.body.style.overflow = "hidden";

  if (titleInput) {
    titleInput.focus();
  }
}

function closeMemoryModal() {
  var modal = document.getElementById("memory-modal");
  var form = document.getElementById("memory-form");

  if (!modal) {
    return;
  }

  modal.hidden = true;
  document.body.style.overflow = "";
  memoryUiState.editingId = null;

  if (form) {
    form.reset();
  }
}

async function saveMemoryFromForm(form) {
  if (isSavingMemory) {
    return;
  }

  var titleInput = document.getElementById("memory-title");
  var categoryInput = document.getElementById("memory-category");
  var notesInput = document.getElementById("memory-notes");
  var tagsInput = document.getElementById("memory-tags");
  var saveButton = form.querySelector('button[type="submit"]');
  var editingId = memoryUiState.editingId;

  isSavingMemory = true;

  try {
    if (saveButton) {
      saveButton.disabled = true;
      saveButton.textContent = editingId ? "Saving Changes..." : "Saving...";
    }

    var input = {
      title: titleInput.value,
      category: categoryInput.value,
      notes: notesInput.value,
      tags: tagsInput ? tagsInput.value : "",
      source: "dashboard"
    };

    var savedMemory = editingId
      ? await MemoryEngine.updateMemory(editingId, input)
      : await MemoryEngine.saveMemory(input);

    closeMemoryModal();
    await loadCommandCenter();

    var memoryPage = document.getElementById("page-memory");
    if (memoryPage && !memoryPage.hidden) {
      await loadMemoryPage();
    }

    if (editingId) {
      await openMemoryDetail(savedMemory.id);
    }

    showToast(editingId ? "Memory updated successfully" : "Memory saved successfully");
  } catch (error) {
    console.error("Failed to save memory:", error);
    showToast(
      editingId
        ? "Could not update memory. Check your Supabase settings and try again."
        : "Could not save memory. Check your Supabase settings and try again."
    );
  } finally {
    isSavingMemory = false;

    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = editingId ? "Save Changes" : "Save";
    }
  }
}

async function loadMemoryPage() {
  var resultsContainer = document.getElementById("memory-search-results");
  var metaElement = document.getElementById("memory-search-meta");

  if (!resultsContainer) {
    return;
  }

  resultsContainer.innerHTML = getLoadingStateHtml("Loading memories...", "Fetching from Supabase.");

  if (metaElement) {
    metaElement.textContent = "";
  }

  try {
    memoryPageState.allMemories = await MemoryEngine.loadMemories();
    renderMemorySearchResults();
  } catch (error) {
    console.error("Failed to load memories:", error);
    resultsContainer.innerHTML = getErrorStateHtml(
      "Could not load memories",
      "Check your Supabase URL, publishable key, and table permissions."
    );
    showToast("Could not load memories. Check your Supabase settings.");
  }
}

function renderMemorySearchResults() {
  var resultsContainer = document.getElementById("memory-search-results");
  var metaElement = document.getElementById("memory-search-meta");

  if (!resultsContainer) {
    return;
  }

  var results = MemoryEngine.searchMemories(
    memoryPageState.allMemories,
    memoryPageState.searchQuery,
    memoryPageState.activeCategory
  );

  resultsContainer.innerHTML = "";

  if (metaElement) {
    var total = memoryPageState.allMemories.length;
    var shown = results.length;

    if (memoryPageState.searchQuery || memoryPageState.activeCategory !== "All") {
      metaElement.textContent = shown + " of " + total + " memories";
    } else {
      metaElement.textContent = total + (total === 1 ? " memory" : " memories");
    }
  }

  if (results.length === 0) {
    resultsContainer.innerHTML = getEmptyStateHtml(
      "No memories found",
      "Try a different search term or category filter."
    );
    return;
  }

  results.forEach(function (memory) {
    resultsContainer.appendChild(createMemoryCard(memory, { preview: true }));
  });
}

function createMemoryCard(memory, options) {
  var settings = options || {};
  var memoryItem = document.createElement("article");
  memoryItem.className = "memory-item memory-item--clickable";
  memoryItem.setAttribute("role", "button");
  memoryItem.setAttribute("tabindex", "0");

  var formattedDate = formatMemoryDate(memory.created_at);
  var notesClass = settings.preview ? "memory-item__notes memory-item__notes--preview" : "memory-item__notes";
  var tagsHtml = buildTagsHtml(memory.tags, 3);
  var owner = memory.owner || MemoryEngine.DEFAULT_OWNER;
  var importance = memory.importance || "Medium";
  var importanceClass = normalizeImportanceClass(importance);
  var confidenceLabel = formatConfidence(memory.confidence_score);

  memoryItem.innerHTML =
    '<div class="memory-item__header">' +
      '<h3 class="memory-item__title">' + escapeHtml(memory.title) + '</h3>' +
      '<span class="memory-item__category">' + escapeHtml(memory.category) + '</span>' +
    '</div>' +
    '<p class="' + notesClass + '">' + escapeHtml(memory.notes) + '</p>' +
    (tagsHtml ? '<div class="memory-item__tags">' + tagsHtml + '</div>' : '') +
    '<div class="memory-item__footer">' +
      '<span class="memory-item__owner">' + escapeHtml(owner) + '</span>' +
      '<span class="memory-item__importance memory-item__importance--' + importanceClass + '">' +
        escapeHtml(importance) +
      '</span>' +
      '<span class="memory-item__confidence">' + escapeHtml(confidenceLabel) + '</span>' +
      '<span class="memory-item__date">' + formattedDate + '</span>' +
    '</div>';

  memoryItem.addEventListener("click", function () {
    openMemoryDetail(memory.id);
  });

  memoryItem.addEventListener("keydown", function (event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openMemoryDetail(memory.id);
    }
  });

  return memoryItem;
}

async function openMemoryDetail(memoryId) {
  var overlay = document.getElementById("memory-detail-overlay");

  if (!overlay) {
    return;
  }

  try {
    var memory = await MemoryEngine.getMemoryById(memoryId);
    var relatedMemories = await MemoryEngine.loadRelatedMemories(memory);

    memoryUiState.activeMemory = memory;

    document.getElementById("memory-detail-category").textContent = memory.category;
    document.getElementById("memory-detail-owner").textContent = memory.owner || MemoryEngine.DEFAULT_OWNER;
    document.getElementById("memory-detail-importance").textContent = memory.importance || "Medium";
    document.getElementById("memory-detail-importance").className =
      "memory-detail__importance memory-detail__importance--" +
      normalizeImportanceClass(memory.importance);
    document.getElementById("memory-detail-confidence").textContent =
      formatConfidence(memory.confidence_score);
    document.getElementById("memory-detail-title").textContent = memory.title;
    document.getElementById("memory-detail-date").textContent = formatMemoryDate(memory.created_at);
    document.getElementById("memory-detail-notes").textContent = memory.notes;

    renderDetailTags(memory.tags || []);
    renderDetailRelated(relatedMemories);

    overlay.hidden = false;
    document.body.style.overflow = "hidden";
  } catch (error) {
    console.error("Failed to open memory detail:", error);
    showToast("Could not load memory details.");
  }
}

function renderDetailTags(tags) {
  var tagsContainer = document.getElementById("memory-detail-tags");

  if (!tagsContainer) {
    return;
  }

  if (!tags.length) {
    tagsContainer.hidden = true;
    tagsContainer.innerHTML = "";
    return;
  }

  tagsContainer.hidden = false;
  tagsContainer.innerHTML = buildTagsHtml(tags);
}

function renderDetailRelated(relatedMemories) {
  var relatedSection = document.getElementById("memory-detail-related");
  var relatedList = document.getElementById("memory-detail-related-list");

  if (!relatedSection || !relatedList) {
    return;
  }

  if (!relatedMemories.length) {
    relatedSection.hidden = true;
    relatedList.innerHTML = "";
    return;
  }

  relatedSection.hidden = false;
  relatedList.innerHTML = "";

  relatedMemories.forEach(function (memory) {
    var item = document.createElement("button");
    item.type = "button";
    item.className = "memory-related-item";

    item.innerHTML =
      '<span class="memory-related-item__title">' + escapeHtml(memory.title) + '</span>' +
      '<span class="memory-related-item__category">' + escapeHtml(memory.category) + '</span>';

    item.addEventListener("click", function () {
      openMemoryDetail(memory.id);
    });

    relatedList.appendChild(item);
  });
}

function closeMemoryDetail() {
  var overlay = document.getElementById("memory-detail-overlay");

  if (!overlay) {
    return;
  }

  overlay.hidden = true;
  document.body.style.overflow = "";
  memoryUiState.activeMemory = null;
}

function buildTagsHtml(tags, limit) {
  var safeTags = Array.isArray(tags) ? tags : [];
  var visibleTags = limit ? safeTags.slice(0, limit) : safeTags;

  if (!visibleTags.length) {
    return "";
  }

  return visibleTags
    .map(function (tag) {
      return '<span class="memory-tag">' + escapeHtml(tag) + '</span>';
    })
    .join("");
}

function formatTagsForInput(tags) {
  return (Array.isArray(tags) ? tags : []).join(", ");
}

function formatConfidence(value) {
  var confidence = Number(value);

  if (!Number.isFinite(confidence)) {
    confidence = 0;
  }

  return "Confidence " + Math.min(100, Math.max(0, Math.round(confidence))) + "%";
}

function getLoadingStateHtml(title, text) {
  return (
    '<div class="empty-state">' +
      '<p class="empty-state__title">' + escapeHtml(title) + '</p>' +
      '<p class="empty-state__text">' + escapeHtml(text) + '</p>' +
    '</div>'
  );
}

function getEmptyStateHtml(title, text) {
  return getLoadingStateHtml(title, text);
}

function getErrorStateHtml(title, text) {
  return getLoadingStateHtml(title, text);
}

function formatMemoryDate(isoString) {
  var date = new Date(isoString);

  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
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
