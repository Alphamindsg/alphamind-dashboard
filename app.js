/**
 * AlphaMind OS — Main application logic
 * Handles navigation, UI, and delegates memory operations to Memory Engine v2.
 */

var memoryPageState = {
  allMemories: [],
  activeCategory: "All",
  searchQuery: "",
  searchTimer: null
};

var isSavingMemory = false;

var IMPORTANCE_CLASS_ALLOWLIST = ["low", "medium", "high", "critical"];

function normalizeImportanceClass(value) {
  var normalized = String(value || "").toLowerCase().trim();

  return IMPORTANCE_CLASS_ALLOWLIST.indexOf(normalized) !== -1 ? normalized : "medium";
}

document.addEventListener("DOMContentLoaded", function () {
  displayCurrentDate();
  setupSidebarNavigation();
  setupQuickActions();
  setupMemoryModal();
  setupMemoryPage();
  setupMemoryDetailPanel();
  renderRecentMemories();
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

function setupSidebarNavigation() {
  var sidebarLinks = document.querySelectorAll(".sidebar__link");

  sidebarLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      var navTarget = link.getAttribute("data-nav");

      if (navTarget === "dashboard") {
        setActiveSidebarLink(sidebarLinks, link);
        showPage("dashboard");
        return;
      }

      if (navTarget === "memory") {
        setActiveSidebarLink(sidebarLinks, link);
        showPage("memory");
        loadMemoryPage();
        return;
      }

      showToast(getComingSoonMessage(navTarget));
    });
  });
}

function setActiveSidebarLink(sidebarLinks, activeLink) {
  sidebarLinks.forEach(function (item) {
    item.classList.remove("sidebar__link--active");
  });

  activeLink.classList.add("sidebar__link--active");
}

function getComingSoonMessage(navTarget) {
  var messages = {
    learning: "Learning module is not connected yet. Atlas will be ready soon.",
    research: "Research module is coming in a future update.",
    trading: "Trading module is coming in a future update.",
    "virtual-influencer": "Virtual Influencer module is coming in a future update.",
    "financial-education": "Financial Education module is coming in a future update.",
    "ai-employees": "AI Employees view is coming in a future update.",
    settings: "Settings are coming in a future update."
  };

  return messages[navTarget] || "This module is coming in a future update.";
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

function setupQuickActions() {
  var addMemoryButton = document.getElementById("btn-add-memory");
  var reviewLearningButton = document.getElementById("btn-review-learning");
  var viewEmployeesButton = document.getElementById("btn-view-employees");

  if (addMemoryButton) {
    addMemoryButton.addEventListener("click", openMemoryModal);
  }

  if (reviewLearningButton) {
    reviewLearningButton.addEventListener("click", function () {
      showToast("Learning module is not connected yet. Atlas will be ready soon.");
    });
  }

  if (viewEmployeesButton) {
    viewEmployeesButton.addEventListener("click", function () {
      showToast("AI Employees view is coming in a future update.");
    });
  }
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

  if (!overlay) {
    return;
  }

  if (closeButton) {
    closeButton.addEventListener("click", closeMemoryDetail);
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

function openMemoryModal() {
  var modal = document.getElementById("memory-modal");
  var titleInput = document.getElementById("memory-title");

  if (!modal) {
    return;
  }

  modal.hidden = false;
  document.body.style.overflow = "hidden";

  if (titleInput) {
    titleInput.focus();
  }
}

function closeMemoryModal() {
  var modal = document.getElementById("memory-modal");

  if (!modal) {
    return;
  }

  modal.hidden = true;
  document.body.style.overflow = "";
}

async function saveMemoryFromForm(form) {
  if (isSavingMemory) {
    return;
  }

  var titleInput = document.getElementById("memory-title");
  var categoryInput = document.getElementById("memory-category");
  var notesInput = document.getElementById("memory-notes");
  var saveButton = form.querySelector('button[type="submit"]');

  isSavingMemory = true;

  try {
    if (saveButton) {
      saveButton.disabled = true;
      saveButton.textContent = "Saving...";
    }

    await MemoryEngine.saveMemory({
      title: titleInput.value,
      category: categoryInput.value,
      notes: notesInput.value,
      source: "dashboard"
    });

    form.reset();
    closeMemoryModal();
    await renderRecentMemories();

    var memoryPage = document.getElementById("page-memory");
    if (memoryPage && !memoryPage.hidden) {
      await loadMemoryPage();
    }

    showToast("Memory saved successfully");
  } catch (error) {
    console.error("Failed to save memory:", error);
    showToast("Could not save memory. Check your Supabase settings and try again.");
  } finally {
    isSavingMemory = false;

    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = "Save";
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

async function renderRecentMemories() {
  var container = document.getElementById("recent-memory-list");

  if (!container) {
    return;
  }

  container.innerHTML = getLoadingStateHtml("Loading memories...", "Fetching the latest notes from Supabase.");

  try {
    var memories = await MemoryEngine.loadMemories({ limit: 20 });
    container.innerHTML = "";

    if (memories.length === 0) {
      container.innerHTML = getEmptyStateHtml(
        "No memories saved yet",
        "Use the Add Memory button to capture your first note."
      );
      return;
    }

    memories.forEach(function (memory) {
      container.appendChild(createMemoryCard(memory, { preview: false }));
    });
  } catch (error) {
    console.error("Failed to load memories:", error);
    container.innerHTML = getErrorStateHtml(
      "Could not load memories",
      "Check your Supabase URL, publishable key, and table permissions."
    );
    showToast("Could not load memories. Check your Supabase settings.");
  }
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

    document.getElementById("memory-detail-category").textContent = memory.category;
    document.getElementById("memory-detail-owner").textContent = memory.owner || MemoryEngine.DEFAULT_OWNER;
    document.getElementById("memory-detail-importance").textContent = memory.importance || "Medium";
    document.getElementById("memory-detail-importance").className =
      "memory-detail__importance memory-detail__importance--" +
      normalizeImportanceClass(memory.importance);
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
}

function buildTagsHtml(tags, limit) {
  var visibleTags = limit ? tags.slice(0, limit) : tags;

  if (!visibleTags.length) {
    return "";
  }

  return visibleTags
    .map(function (tag) {
      return '<span class="memory-tag">' + escapeHtml(tag) + '</span>';
    })
    .join("");
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
