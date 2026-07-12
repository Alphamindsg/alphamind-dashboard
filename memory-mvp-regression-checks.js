"use strict";

var assert = require("node:assert/strict");
var fs = require("node:fs");
var vm = require("node:vm");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function createFakeSupabase(initialRows, options) {
  var settings = options || {};
  var rows = clone(initialRows || []);
  var nextId = rows.reduce(function (maximum, row) {
    return Math.max(maximum, Number(row.id) || 0);
  }, 0) + 1;

  function missingColumnError() {
    return {
      data: null,
      error: {
        message: "Could not find the 'confidence_score' column of 'company_memories' in the schema cache"
      }
    };
  }

  function createBuilder() {
    var action = "select";
    var selectedColumns = "";
    var insertValues = [];
    var updateValues = null;
    var filters = [];
    var inFilter = null;
    var orderColumn = null;
    var orderAscending = true;
    var rowLimit = null;
    var executed = false;
    var executionResult = null;

    function usesConfidence() {
      return (
        selectedColumns.indexOf("confidence_score") !== -1 ||
        (updateValues && Object.prototype.hasOwnProperty.call(updateValues, "confidence_score")) ||
        insertValues.some(function (row) {
          return Object.prototype.hasOwnProperty.call(row, "confidence_score");
        })
      );
    }

    function matches(row) {
      var matchesEquals = filters.every(function (filter) {
        return row[filter.column] === filter.value;
      });
      var matchesIn = !inFilter || inFilter.values.indexOf(row[inFilter.column]) !== -1;
      return matchesEquals && matchesIn;
    }

    function execute() {
      if (executed) {
        return executionResult;
      }

      executed = true;

      if (settings.missingConfidenceColumn && usesConfidence()) {
        executionResult = missingColumnError();
        return executionResult;
      }

      if (action === "insert") {
        var inserted = insertValues.map(function (value) {
          var row = Object.assign(
            {
              id: nextId,
              created_at: "2026-07-12T01:00:00.000Z"
            },
            clone(value)
          );
          nextId += 1;
          rows.push(row);
          return clone(row);
        });
        executionResult = { data: inserted[0] || null, error: null };
        return executionResult;
      }

      if (action === "update") {
        var updated = null;
        rows = rows.map(function (row) {
          if (!matches(row)) {
            return row;
          }

          var changed = Object.assign({}, row, clone(updateValues));
          updated = clone(changed);
          return changed;
        });
        executionResult = { data: updated, error: null };
        return executionResult;
      }

      var selected = rows.filter(matches).map(clone);

      if (orderColumn) {
        selected.sort(function (a, b) {
          var left = a[orderColumn] || "";
          var right = b[orderColumn] || "";
          return orderAscending
            ? String(left).localeCompare(String(right))
            : String(right).localeCompare(String(left));
        });
      }

      if (rowLimit !== null) {
        selected = selected.slice(0, rowLimit);
      }

      executionResult = { data: selected, error: null };
      return executionResult;
    }

    var builder = {
      select: function (columns) {
        selectedColumns = columns || "";
        return builder;
      },
      insert: function (values) {
        action = "insert";
        insertValues = clone(values || []);
        return builder;
      },
      update: function (values) {
        action = "update";
        updateValues = clone(values || {});
        return builder;
      },
      eq: function (column, value) {
        filters.push({ column: column, value: value });
        return builder;
      },
      in: function (column, values) {
        inFilter = { column: column, values: clone(values || []) };
        return builder;
      },
      order: function (column, options) {
        orderColumn = column;
        orderAscending = !options || options.ascending !== false;
        return builder;
      },
      limit: function (value) {
        rowLimit = value;
        return builder;
      },
      single: function () {
        var result = execute();

        if (Array.isArray(result.data)) {
          return Promise.resolve({ data: result.data[0] || null, error: result.error });
        }

        return Promise.resolve(result);
      },
      then: function (resolve, reject) {
        return Promise.resolve(execute()).then(resolve, reject);
      }
    };

    return builder;
  }

  return {
    from: function (table) {
      assert.equal(table, "company_memories");
      return createBuilder();
    },
    getRows: function () {
      return clone(rows);
    }
  };
}

function loadMemoryEngine(fakeSupabase) {
  var context = {
    window: {
      supabaseClient: fakeSupabase
    }
  };

  vm.createContext(context);
  vm.runInContext(fs.readFileSync("memory-engine.js", "utf8"), context, {
    filename: "memory-engine.js"
  });

  return context.window.MemoryEngine;
}

var seedRows = [
  {
    id: 1,
    title: "Q3 roadmap decision",
    category: "Strategy",
    notes: "Approved roadmap decision with customer evidence and a measured result.",
    source: "dashboard",
    created_at: "2026-07-12T00:00:00.000Z",
    owner: "Athena",
    importance: "High",
    confidence_score: 85,
    tags: ["strategy", "roadmap", "decision"],
    related_memory_ids: []
  },
  {
    id: 2,
    title: "Customer research summary",
    category: "Research",
    notes: "Research source and customer evidence for the product roadmap.",
    source: "dashboard",
    created_at: "2026-07-11T00:00:00.000Z",
    owner: "Athena",
    importance: "Medium",
    confidence_score: 80,
    tags: ["research", "feedback", "roadmap"],
    related_memory_ids: []
  },
  {
    id: 3,
    title: "Operations follow-up",
    category: "Operations",
    notes: "Routine operational note.",
    source: "dashboard",
    created_at: "2026-07-10T00:00:00.000Z",
    owner: "Athena",
    importance: "Low",
    confidence_score: 55,
    tags: ["operations"],
    related_memory_ids: []
  }
];

async function run() {
  var fakeSupabase = createFakeSupabase(seedRows);
  var engine = loadMemoryEngine(fakeSupabase);

  assert.deepEqual(
    Array.from(engine.normalizeTags(["Q3 Plan", "q3-plan", " Board Decision ", ""])),
    ["q3-plan", "board-decision"]
  );

  var tags = Array.from(
    engine.generateTags(
      "Launch decision",
      "Strategy",
      "Approved customer roadmap priority.",
      "board, q3"
    )
  );
  assert.equal(tags.includes("board"), true);
  assert.equal(tags.includes("q3"), true);
  assert.equal(tags.includes("strategy"), true);
  assert.equal(tags.includes("decision"), true);

  var sparseConfidence = engine.calculateConfidence("Idea", "", "Maybe useful.", []);
  var evidenceConfidence = engine.calculateConfidence(
    "Approved customer decision",
    "Strategy",
    "Verified evidence from a customer meeting and a measured result supports this decision.",
    ["strategy", "customer"]
  );
  assert.equal(evidenceConfidence > sparseConfidence, true);
  assert.equal(evidenceConfidence <= 95, true);

  var nullConfidenceMemory = engine.normalizeMemory({
    id: 10,
    title: "Approved operating decision",
    category: "Strategy",
    notes: "Verified evidence from a meeting supports this decision.",
    tags: ["strategy", "decision"],
    confidence_score: null
  });
  assert.equal(nullConfidenceMemory.confidence_score > 0, true);
  assert.equal(nullConfidenceMemory.confidence_score, 80);

  var related = Array.from(
    engine.findRelatedMemoryIds(
      { id: 1, category: "Strategy", tags: ["roadmap", "decision"] },
      seedRows
    )
  );
  assert.equal(related.includes(1), false);
  assert.equal(related[0], 2);
  assert.equal(related.length <= 3, true);

  var saved = await engine.saveMemory({
    title: "CEO weekly decision",
    category: "Strategy",
    notes: "Approved decision with meeting evidence and a roadmap result.",
    tags: "ceo, weekly",
    source: "dashboard"
  });
  assert.equal(saved.title, "CEO weekly decision");
  assert.equal(saved.tags.includes("ceo"), true);
  assert.equal(saved.tags.includes("weekly"), true);
  assert.equal(saved.confidence_score >= 20, true);

  var updated = await engine.updateMemory(saved.id, {
    title: "CEO weekly product decision",
    category: "Strategy",
    notes: "Verified decision from the weekly meeting with customer evidence and a measured result.",
    tags: "ceo, product, approved"
  });
  assert.equal(updated.title, "CEO weekly product decision");
  assert.equal(updated.tags.includes("product"), true);
  assert.equal(updated.related_memory_ids.includes(updated.id), false);

  var userTags = Array.from(engine.getManualTags(updated));
  assert.equal(userTags.includes("ceo"), true);
  assert.equal(userTags.includes("approved"), true);
  assert.equal(userTags.includes("product"), false);
  assert.equal(userTags.includes("strategy"), false);
  assert.equal(userTags.includes("decision"), false);

  var retagged = await engine.updateMemory(updated.id, {
    title: "Weekly operating notes revised",
    category: "Operations",
    notes: "Routine follow-up notes for the next review.",
    tags: userTags
  });
  assert.equal(retagged.tags.includes("operations"), true);
  assert.equal(retagged.tags.includes("strategy"), false);
  assert.equal(retagged.tags.includes("decision"), false);

  var allRows = await engine.loadMemories();
  assert.equal(engine.searchMemories(allRows, "product", "All").length >= 1, true);
  assert.equal(engine.searchMemories(allRows, String(updated.confidence_score), "All").length >= 1, true);

  var legacySupabase = createFakeSupabase(
    seedRows.map(function (row) {
      var legacy = clone(row);
      delete legacy.confidence_score;
      return legacy;
    }),
    { missingConfidenceColumn: true }
  );
  var legacyEngine = loadMemoryEngine(legacySupabase);
  var legacyRows = await legacyEngine.loadMemories();
  assert.equal(Number.isFinite(legacyRows[0].confidence_score), true);

  var legacySaved = await legacyEngine.saveMemory({
    title: "Legacy schema memory",
    category: "Operations",
    notes: "Verified operational result saved before the confidence migration.",
    tags: "legacy, operations"
  });
  assert.equal(Number.isFinite(legacySaved.confidence_score), true);
  assert.equal(
    Object.prototype.hasOwnProperty.call(
      legacySupabase.getRows().find(function (row) {
        return row.id === legacySaved.id;
      }),
      "confidence_score"
    ),
    false
  );

  var legacyUpdated = await legacyEngine.updateMemory(legacySaved.id, {
    title: "Legacy schema memory updated",
    category: "Operations",
    notes: "Verified updated result without the optional confidence column.",
    tags: "legacy, edited"
  });
  assert.equal(legacyUpdated.title, "Legacy schema memory updated");
  assert.equal(legacyUpdated.tags.includes("edited"), true);

  var htmlSource = fs.readFileSync("index.html", "utf8");
  var appSource = fs.readFileSync("app.js", "utf8");
  assert.equal(htmlSource.indexOf('id="btn-edit-memory"') !== -1, true);
  assert.equal(htmlSource.indexOf('id="memory-tags"') !== -1, true);
  assert.equal(htmlSource.indexOf('id="memory-detail-confidence"') !== -1, true);
  assert.equal(appSource.indexOf("MemoryEngine.updateMemory") !== -1, true);

  console.log("Memory MVP regression checks passed.");
}

run().catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
