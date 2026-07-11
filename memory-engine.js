/**
 * AlphaMind OS — Memory Engine v2
 * Central module for saving, loading, searching, and organizing company memories.
 * Future AI employees (Athena, Atlas, Orion, etc.) will use this same engine.
 */

(function () {
  "use strict";

  var DEFAULT_OWNER = "Athena";
  var MEMORY_TABLE = "company_memories";
  var MEMORY_COLUMNS =
    "id, title, category, notes, source, created_at, owner, importance, tags, related_memory_ids";
  var MAX_RELATED = 3;
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

  /**
   * Extract rule-based tags from memory content. No external API.
   */
  function generateTags(title, category, notes) {
    var combined = (title + " " + notes).toLowerCase();
    var tags = [];
    var seen = {};

    function addTag(tag) {
      var normalized = tag.toLowerCase().trim();

      if (!normalized || seen[normalized]) {
        return;
      }

      seen[normalized] = true;
      tags.push(normalized);
    }

    if (category) {
      addTag(category.toLowerCase());
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

    return tags.slice(0, 8);
  }

  /**
   * Calculate importance as text: Low, Medium, High, or Critical.
   */
  function calculateImportance(title, category, notes) {
    var combined = (title + " " + notes).toLowerCase();
    var score = 0;

    if (category === "Strategy") {
      score += 2;
    }

    if (/\b(decision|critical|urgent|priority|approve|roadmap)\b/i.test(combined)) {
      score += 2;
    }

    if (notes.length > 200) {
      score += 1;
    }

    if (category === "Personal" && notes.length < 80) {
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
   * Score how related two memories are based on tags and category.
   */
  function relatednessScore(memoryA, memoryB) {
    if (memoryA.id === memoryB.id) {
      return 0;
    }

    var score = 0;
    var tagsA = memoryA.tags || [];
    var tagsB = memoryB.tags || [];

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
   * Save a new memory with auto-generated tags, importance, and owner.
   */
  async function saveMemory(input) {
    var supabaseClient = getSupabaseClient();
    var title = input.title.trim();
    var category = input.category;
    var notes = input.notes.trim();
    var tags = generateTags(title, category, notes);
    var importance = calculateImportance(title, category, notes);

    var insertResult = await supabaseClient
      .from(MEMORY_TABLE)
      .insert([
        {
          title: title,
          category: category,
          notes: notes,
          source: input.source || "dashboard",
          owner: DEFAULT_OWNER,
          importance: importance,
          tags: tags,
          related_memory_ids: []
        }
      ])
      .select(MEMORY_COLUMNS)
      .single();

    if (insertResult.error) {
      throw insertResult.error;
    }

    var savedMemory = insertResult.data;
    var existingMemories = await loadMemories({ limit: 200 });
    var relatedIds = findRelatedMemoryIds(savedMemory, existingMemories);

    if (relatedIds.length > 0) {
      var updateResult = await supabaseClient
        .from(MEMORY_TABLE)
        .update({ related_memory_ids: relatedIds })
        .eq("id", savedMemory.id)
        .select(MEMORY_COLUMNS)
        .single();

      if (updateResult.error) {
        throw updateResult.error;
      }

      return updateResult.data;
    }

    return savedMemory;
  }

  /**
   * Load memories from Supabase, newest first.
   */
  async function loadMemories(options) {
    var supabaseClient = getSupabaseClient();
    var settings = options || {};
    var query = supabaseClient
      .from(MEMORY_TABLE)
      .select(MEMORY_COLUMNS)
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
   * Load a single memory by ID.
   */
  async function getMemoryById(id) {
    var supabaseClient = getSupabaseClient();

    var result = await supabaseClient
      .from(MEMORY_TABLE)
      .select(MEMORY_COLUMNS)
      .eq("id", id)
      .single();

    if (result.error) {
      throw result.error;
    }

    return result.data;
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

    var result = await supabaseClient
      .from(MEMORY_TABLE)
      .select(MEMORY_COLUMNS)
      .in("id", relatedIds);

    if (result.error) {
      throw result.error;
    }

    return result.data || [];
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
      var tagsText = (memory.tags || []).join(" ");

      return (
        (memory.title || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.category || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.notes || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        tagsText.toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.owner || "").toLowerCase().indexOf(normalizedQuery) !== -1 ||
        (memory.importance || "").toLowerCase().indexOf(normalizedQuery) !== -1
      );
    });
  }

  window.MemoryEngine = {
    DEFAULT_OWNER: DEFAULT_OWNER,
    CATEGORIES: ["All", "Strategy", "Learning", "Research", "Trading", "Operations", "Personal"],
    generateTags: generateTags,
    calculateImportance: calculateImportance,
    findRelatedMemoryIds: findRelatedMemoryIds,
    saveMemory: saveMemory,
    loadMemories: loadMemories,
    getMemoryById: getMemoryById,
    loadRelatedMemories: loadRelatedMemories,
    searchMemories: searchMemories
  };
})();
