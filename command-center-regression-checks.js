"use strict";

var assert = require("node:assert/strict");
var fs = require("node:fs");
var vm = require("node:vm");

function normalizeTags(input) {
  var values = Array.isArray(input) ? input : String(input || "").split(",");

  return values
    .map(function (value) {
      return String(value || "").toLowerCase().trim();
    })
    .filter(Boolean);
}

var memoryEngine = {
  normalizeTags: normalizeTags
};
var context = {
  document: {
    addEventListener: function () {}
  },
  window: {
    MemoryEngine: memoryEngine
  },
  MemoryEngine: memoryEngine,
  console: console
};

vm.createContext(context);
vm.runInContext(fs.readFileSync("app.js", "utf8"), context, {
  filename: "app.js"
});

var memories = [
  {
    id: 1,
    title: "First focus",
    category: "Strategy",
    notes: "Review the first manually selected priority.",
    created_at: "2026-07-12T04:00:00.000Z",
    importance: "High",
    tags: ["focus-1", "waiting-ceo", "executive-decision"]
  },
  {
    id: 2,
    title: "Second focus",
    category: "Operations",
    notes: "Review the second manually selected priority.",
    created_at: "2026-07-12T03:00:00.000Z",
    importance: "Medium",
    tags: ["focus-2"]
  },
  {
    id: 3,
    title: "Third focus",
    category: "Engineering",
    notes: "Review the third manually selected priority.",
    created_at: "2026-07-12T02:00:00.000Z",
    importance: "Critical",
    tags: ["focus-3", "waiting-ceo", "pr-approval"]
  },
  {
    id: 4,
    title: "Unselected critical item",
    category: "Strategy",
    notes: "This record is critical but is not manually selected for focus.",
    created_at: "2026-07-12T05:00:00.000Z",
    importance: "Critical",
    tags: ["priority"]
  },
  {
    id: 5,
    title: "Completed documentation review",
    category: "Learning",
    notes: "The approved documentation review is complete.",
    created_at: "2026-07-12T01:00:00.000Z",
    importance: "Medium",
    tags: ["completed"]
  },
  {
    id: 6,
    title: "Recent product knowledge",
    category: "Research",
    notes: "A recent research finding for the CEO.",
    created_at: "2026-07-12T00:30:00.000Z",
    importance: "High",
    tags: ["research"]
  }
];

var focus = Array.from(context.selectFocusMemories(memories));
assert.deepEqual(
  focus.map(function (memory) {
    return memory.id;
  }),
  [1, 2, 3]
);
assert.equal(focus.length, 3);
assert.equal(
  focus.some(function (memory) {
    return memory.id === 4;
  }),
  false,
  "Critical records must not become focus items without explicit focus tags"
);

var gappedFocus = Array.from(context.selectFocusMemories([memories[1], memories[2]]));
assert.deepEqual(
  gappedFocus.map(function (memory) {
    return memory.command_center_focus_position;
  }),
  [2, 3]
);
assert.equal(context.getCommandItemBadge(gappedFocus[0], "focus", 0), "2");

var waiting = Array.from(context.selectWaitingForCeoMemories(memories));
assert.deepEqual(
  waiting.map(function (memory) {
    return memory.id;
  }),
  [1, 3]
);
assert.equal(context.getWaitingReason(memories[0]), "Executive decision");
assert.equal(context.getWaitingReason(memories[2]), "PR approval");

var progress = Array.from(context.selectProgressMemories(memories));
assert.deepEqual(
  progress.map(function (memory) {
    return memory.id;
  }),
  [5]
);

var recent = Array.from(
  context.selectRecentKnowledge(memories, focus.concat(waiting, progress))
);
assert.deepEqual(
  recent.map(function (memory) {
    return memory.id;
  }),
  [4, 6]
);

assert.equal(
  context.createQuickCaptureTitle(
    "A concise pilot observation that should become a bounded title. Extra detail follows."
  ),
  "A concise pilot observation that should become a bounded title"
);
assert.equal(context.createQuickCaptureTitle("   "), "Quick capture");
assert.equal(context.truncateText("Short text", 20), "Short text");
assert.equal(context.truncateText("This text is longer than ten", 10), "This text…");

var htmlSource = fs.readFileSync("index.html", "utf8");
var appSource = fs.readFileSync("app.js", "utf8");
var sidebarLinks = (htmlSource.match(/class="sidebar__link/g) || []).length;

[
  'id="current-time"',
  'id="current-date"',
  'id="today-focus-list"',
  'id="waiting-ceo-list"',
  'id="recent-knowledge-list"',
  'id="quick-capture-form"',
  'id="today-progress-list"',
  'id="system-pulse-list"'
].forEach(function (marker) {
  assert.equal(htmlSource.indexOf(marker) !== -1, true, marker + " must exist");
});

assert.equal(sidebarLinks, 2, "Only Command Center and Memory belong in MVP navigation");
assert.equal(htmlSource.indexOf("Ask AlphaMind"), -1, "Backlog-only feature must not appear in UI");
assert.equal(appSource.indexOf('focusTags: ["focus-1", "focus-2", "focus-3"]') !== -1, true);
assert.equal(appSource.indexOf('waitingTag: "waiting-ceo"') !== -1, true);
assert.equal(appSource.indexOf('source: "command-center"') !== -1, true);
assert.equal(appSource.indexOf("MemoryEngine.saveMemory") !== -1, true);

console.log("CEO Command Center regression checks passed.");
