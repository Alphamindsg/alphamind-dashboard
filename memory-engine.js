/**
 * AlphaMind OS — Memory MVP Engine (MEM-001)
 * Create, edit, load, search, tag, score, and relate company memories.
 */

(function () {
  "use strict";

  var DEFAULT_OWNER = "Athena";
  var MEMORY_TABLE = "company_memories";
  var MEMORY_COLUMNS_BASE =
    "id, title, category, notes, source, created_at, owner, importance, tags, related_memory_ids";
  var MEMORY_COLUMNS_WITH_CONFIDENCE = MEMORY_COLUMNS_BASE + ", confidence_score";
  var MAX_RELATED = 3;
  var MAX_TAGS = 12;
  var confidenceColumnAvailable = null;
  var STOP_WORDS = {
    the: true,
    and: true,
    for: true,
    with: true,
    this: true,
    that: true,
    from: true,
    have: true,
    will: true,
    about: true,
    into: true,
    your: true,
    our: true,
    are: true,
    was: true,
    were: true,
    been: true,
    being: true,
    also: true,
    just: true,
    not: true,
    but: true,
    can: true,
    all: true,
    any: true,
    use: true,
    using: true
  };

  var KEYWORD_TAGS = [
    { pattern: /\b(decision|decided|approve|approved)\b/i, tag: "decision" },
    { pattern: /\b(roadmap|milestone|phase|sprint)\b/i, tag: "roadmap" },
    { pattern: /\b(priority|priorities|urgent|critical)\b/i, tag: "priority" },
    { pattern: /\b(lesson|learned|learning|insight)\b/i, tag: "learning" },
    { pattern: /\b(research|analysis|study|report)\b/i, tag: "research" },
    { pattern: /\b(trade|trading|market|portfolio)\b/i, tag: "trading" },
    { pattern: /\b(customer|feedback|client|user)\b/i, tag: "feedback" },
    { pattern: /\b(architecture|system|design|engine)\b/i, tag: "architecture" },
    { pattern: /\b(strategy|vision|goal|objective)\b/i, tag: "strategy" },
    { pattern: /\b(mistake|error|failure|fix)\b/i, tag: "lesson" },
    { pattern: /\b(idea|concept|proposal)\b/i, tag: "idea" }
  ];

  function getSupabaseClient() {
    if (!window.supabaseClient) {
      throw new Error("Supabase client is not available.");
    }

    return window.supabaseClient;
  }

  function clampNumber(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function normalizeTag(tag) {
    return String(tag || "")
      .toLowerCase()
      .trim()
      .replace(/^#+/, "")
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 32);
  }

  function normalizeTags(input) {
    var values = Array.isArray(input) ? input : String(input || "").split(",");
    var tags = [];
    var seen = Object.create(null);

    values.forEach(function (value) {
      var tag = normalizeTag(value);

      if (!tag || seen[tag] || tags.length >= MAX_TAGS) {
        return;
      }

      seen[tag] = true;
      tags.push(tag);
    });

    return tags;
  }

  /**
   * Extract deterministic tags from memory content and merge user-entered tags.
   */
  function generateTags(title, category, notes, manualTags) {
    var combined = (String(title || "") + " " + String(notes || "")).toLowerCase();
    var tags = [];
    var seen = Object.create(null);

    function addTag(tag) {
      var normalized = normalizeTag(tag);

      if (!normalized || seen[normalized] || tags.length >= MAX_TAGS) {
        return;
      }

      seen[normalized] = true;
      tags.push(normalized);
    }

    normalizeTags(manualTags).forEach(addTag);

    if (category) {
      addTag(category);
    }

    KEYWORD_TAGS.forEach(function (entry) {
      if (entry.pattern.test(combined)) {
        addTag(entry.tag);
      }
    });

    combined
      .replace(/[^a-z0-9\s-]/g, " ")
      .split(/\s+/)
      .forEach(function (word) {
        if (word.length >= 4 && !STOP_WORDS[word]) {
          addTag(word);
        }
      });

    return tags;
  }

  /**
   * Calculate importance as text: Low, Medium, High, or Critical.
   */
  function calculateImportance(title, category, notes) {
    var combined = (String(title || "") + " " + String(notes || "")).toLowerCase();
    var score = 0;

    if (category === "Strategy") {
      score += 2;
    }

    if (/\b(decision|critical|urgent|priority|approve|roadmap)\b/i.test(combined)) {
      score += 2;
    }

    if (String(notes || "").length > 200) {
      score += 1;
    }

    if (category === "Personal" && String(notes || "").length < 80) {
      score -= 1;
    }

    if (score >= 4) {
      return "Critical";
    }

    if (score >= 2) {
      return "High";
    }

    if (score <= 0) {
      return "Low";
    }

    return "Medium";
  }

  /**
   * Deterministic content-confidence score. This measures completeness and
   * evidence signals; it is not an AI claim that the memory is objectively true.
   */
  function calculateConfidence(title, category, notes, tags) {
    var normalizedTitle = String(title || "").trim();
    var normalizedNotes = String(notes || "").trim();
    var combined = (normalizedTitle + " " + normalizedNotes).toLowerCase();
    var score = 35;

    if (normalizedTitle.length >= 8) {
      score += 10;
    }

    if (category) {
      score += 10;
    }

    if (normalizedNotes.length >= 40) {
      score += 10;
    }

    if (normalizedNotes.length >= 120) {
      score += 10;
    }

    if (normalizedNotes.length >= 250) {
      score += 5;
    }

    if (normalizeTags(tags).length >= 2) {
      score += 5;
    }

    if (/\b(approved|confirmed|verified|evidence|source|metric|result|decision|meeting|commit)\b/i.test(combined)) {
      score += 10;
    }

    if (/\b(unknown|uncertain|unverified|assumption|estimate|maybe)\b/i.test(combined)) {
      score -= 10;
    }

    return clampNumber(Math.round(score), 20, 95);
  }

  function buildMemoryValues(input) {
    var title = String(input.title || "").trim();
    var category = String(input.category || "").trim();
    var notes = String(input.notes || "").trim();

    if (!title || !category || !notes) {
      throw new Error("Title, category, and notes are required.");
    }

    var tags = generateTags(title, category, notes, input.tags || []);

    return {
      title: title,
      category: category,
      notes: notes,
      tags: tags,
      importance: calculateImportance(title, category, notes),
      confidence_score: calculateConfidence(title, category, notes, tags)
    };
  }

  function getManualTags(memory) {
    var automaticTags = generateTags(
      memory && memory.title,
      memory && memory.category,
      memory && memory.notes,
      []
    );
    var automaticTagSet = Object.create(null);

    automaticTags.forEach(function (tag) {
      automaticTagSet[tag] = true;
    });

    return normalizeTags((memory && memory.tags) || []).filter(function (tag) {
      return !automaticTagSet[tag];
    });
  }

  function normalizeMemory(memory) {
    var normalized = Object.assign({}, memory || {});
    var rawConfidence = normalized.confidence_score;
    var confidence =
      rawConfidence === null || rawConfidence === undefined || rawConfidence === ""
        ? Number.NaN
        : Number(rawConfidence);

    normalized.tags = normalizeTags(normalized.tags || []);
    normalized.related_memory_ids = Array.isArray(normalized.related_memory_ids)
      ? normalized.related_memory_ids
      : [];

    if (!Number.isFinite(confidence)) {
      confidence = calculateConfidence(
        normalized.title,
        normalized.category,
        normalized.notes,
        normalized.tags
      );
    }

    normalized.confidence_score = clampNumber(Math.round(confidence), 0, 100);

    return normalized;
  }

  function isMissingConfidenceColumn(error) {
    var message = String(
      (error && (error.message || error.details || error.hint || error.code)) || ""
    ).toLowerCase();

    return (
      message.indexOf("confidence_score") !== -1 &&
      (message.indexOf("column") !== -1 || message.indexOf("schema cache") !== -1)
    );
  }

  function withoutConfidence(payload) {
    var legacyPayload = Object.assign({}, payload);
    delete legacyPayload.confidence_score;
    return legacyPayload;
  }

  async function selectMemoryData(buildQuery) {
    var result;

    if (confidenceColumnAvailable !== false) {
      result = await buildQuery(MEMORY_COLUMNS_WITH_CONFIDENCE);

      if (!result.error) {
        confidenceColumnAvailable = true;
        return result;
      }

      if (!isMissingConfidenceColumn(result.error)) {
        return result;
      }

      confidenceColumnAvailable = false;
    }

    return buildQuery(MEMORY_COLUMNS_BASE);
  }

  async function insertMemoryRow(payload) {
    var supabaseClient = getSupabaseClient();
    var result;

    if (confidenceColumnAvailable !== false) {
      result = await supabaseClient
        .from(MEMORY_TABLE)
        .insert([payload])
        .select(MEMORY_COLUMNS_WITH_CONFIDENCE)
        .single();

      if (!result.error) {
        confidenceColumnAvailable = true;
        return result;
      }

      if (!isMissingConfidenceColumn(result.error)) {
        return result;
      }

      confidenceColumnAvailable = false;
    }

    return supabaseClient
      .from(MEMORY_TABLE)
      .insert([withoutConfidence(payload)])
      .select(MEMORY_COLUMNS_BASE)
      .single();
  }

  async function updateMemoryRow(id, payload) {
    var supabaseClient = getSupabaseClient();
    var result;

    if (confidenceColumnAvailable !== false) {
      result = await supabaseClient
        .from(MEMORY_TABLE)
        .update(payload)
        .eq("id", id)
        .select(MEMORY_COLUMNS_WITH_CONFIDENCE)
        .single();

      if (!result.error) {
        confidenceColumnAvailable = true;
        return result;
      }

      if (!isMissingConfidenceColumn(result.error)) {
        return result;
      }

      confidenceColumnAvailable = false;
    }

    return supabaseClient
      .from(MEMORY_TABLE)
      .update(withoutConfidence(payload))
      .eq("id", id)
      .select(MEMORY_COLUMNS_BASE)
      .single();
  }

  /**
   * Score how related two memories are based on tags and category.
   */
  function relatednessScore(memoryA, memoryB) {
    if (memoryA.id === memoryB.id) {
      return 0;
    }

    var score = 0;
    var tagsA = normalizeTags(memoryA.tags || []);
    var tagsB = normalizeTags(memoryB.tags || []);

    if (memoryA.category && memoryA.category === memoryB.category) {
      score += 2;
    }

    tagsA.forEach(function (tag) {
      if (tagsB.indexOf(tag) !== -1) {
        score += 1;
      }
    });

    return score;
  }

  /**
   * Find the most related memory IDs for a given memory.
   */
  function findRelatedMemoryIds(targetMemory, allMemories) {
    return allMemories
      .map(function (memory) {
        return {
          id: memory.id,
          score: relatednessScore(targetMemory, memory)
        };
      })
      .filter(function (entry) {
        return entry.score > 0;
      })
      .sort(function (a, b) {
        return b.score - a.score;
      })
      .slice(0, MAX_RELATED)
      .map(function (entry) {
        return entry.id;
      });
  }

  /**
   * Save a new memory with user tags, automatic tags, confidence, importance,
   * and simple related-memory links.
   */
  async function saveMemory(input) {
    var values = buildMemoryValues(input);
    var insertResult = await insertMemoryRow({
      title: values.title,
      category: values.category,
      notes: values.notes,
      source: input.source || "dashboard",
      owner: DEFAULT_OWNER,
      importance: values.importance,
      confidence_score: values.confidence_score,
      tags: values.tags,
      related_memory_ids: []
    });

    if (insertResult.error) {
      throw insertResult.error;
    }

    var savedMemory = normalizeMemory(insertResult.data);
    var existingMemories = await loadMemories({ limit: 200 });
    var relatedIds = findRelatedMemoryIds(savedMemory, existingMemories);

    if (relatedIds.length > 0) {
      var relatedUpdate = await updateMemoryRow(savedMemory.id, {
        related_memory_ids: relatedIds
      });

      if (relatedUpdate.error) {
        throw relatedUpdate.error;
      }

      return normalizeMemory(relatedUpdate.data);
    }

    return savedMemory;
  }

  /**
   * Edit an existing memory and recalculate derived metadata.
   */
  async function updateMemory(id, input) {
    var values = buildMemoryValues(input);
    var existingMemories = await loadMemories({ limit: 200 });
    var targetMemory = {
      id: id,
      category: values.category,
      tags: values.tags
    };
    var relatedIds = findRelatedMemoryIds(targetMemory, existingMemories);
    var updateResult = await updateMemoryRow(id, {
      title: values.title,
      category: values.category,
      notes: values.notes,
      importance: values.importance,
      confidence_score: values.confidence_score,
      tags: values.tags,
      related_memory_ids: relatedIds
    });

    if (updateResult.error) {
      throw updateResult.error;
    }

    return normalizeMemory(updateResult.data);
  }

  /**
   * Load memories from Supabase, newest first.
   */
  async function loadMemories(options) {
    var supabaseClient = getSupabaseClient();
    var settings = options || {};
    var result = await selectMemoryData(function (columns) {
      var query = supabaseClient
        .from(MEMORY_TABLE)
        .select(columns)
        .order("created_at", { ascending: false });

      if (settings.limit) {
        query = query.limit(settings.limit);
      }

      return query;
    });

    if (result.error) {
      throw result.error;
    }

    return (result.data || []).map(normalizeMemory);
  }

  /**
   * Load a single memory by ID.
   */
  async function getMemoryById(id) {
    var supabaseClient = getSupabaseClient();
    var result = await selectMemoryData(function (columns) {
      return supabaseClient
        .from(MEMORY_TABLE)
        .select(columns)
        .eq("id", id)
        .single();
    });

    if (result.error) {
      throw result.error;
    }

    return normalizeMemory(result.data);
  }

  /**
   * Load related memories for a memory using stored related_memory_ids.
   */
  async function loadRelatedMemories(memory) {
    var relatedIds = memory.related_memory_ids || [];

    if (relatedIds.length === 0) {
      return [];
    }

    var supabaseClient = getSupabaseClient();
    var result = await selectMemoryData(function (columns) {
      return supabaseClient
        .from(MEMORY_TABLE)
        .select(columns)
        .in("id", relatedIds);
    });

    if (result.error) {
      throw result.error;
    }

    return (result.data || []).map(normalizeMemory);
  }

  /**
   * Filter memories by search query and optional category.
   */
  function searchMemories(memories, query, category) {
    var normalizedQuery = (query || "").trim().toLowerCase();
    var filtered = memories;

    if (category && category !== "All") {
      filtered = filtered.filter(function (memory) {
        return memory.category === category;
      });
    }

    if (!normalizedQuery) {
      return filtered;
    }

    return filtered.filter(function (memory) {
      var tagsText = normalizeTags(memory.tags || []).join(" ");
      var confidenceText = String(normalizeMemory(memory).confidence_score);

      return (
        (memory.title || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.category || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.notes || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        tagsText.toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.owner || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.importance || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        confidenceText.indexOf(normalizedQuery) !== -1
      );
    });
  }

  window.MemoryEngine = {
    DEFAULT_OWNER: DEFAULT_OWNER,
    CATEGORIES: ["All", "Strategy", "Learning", "Research", "Trading", "Operations", "Personal"],
    normalizeTags: normalizeTags,
    generateTags: generateTags,
    calculateImportance: calculateImportance,
    calculateConfidence: calculateConfidence,
    getManualTags: getManualTags,
    normalizeMemory: normalizeMemory,
    findRelatedMemoryIds: findRelatedMemoryIds,
    saveMemory: saveMemory,
    updateMemory: updateMemory,
    loadMemories: loadMemories,
    getMemoryById: getMemoryById,
    loadRelatedMemories: loadRelatedMemories,
    searchMemories: searchMemories
  };
})();
