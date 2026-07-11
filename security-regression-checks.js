"use strict";

var assert = require("node:assert/strict");
var fs = require("node:fs");
var vm = require("node:vm");

function loadBrowserScript(fileName) {
  var context = {
    document: {
      addEventListener: function () {}
    }
  };

  vm.createContext(context);
  vm.runInContext(fs.readFileSync(fileName, "utf8"), context, {
    filename: fileName
  });

  return context;
}

var appContext = loadBrowserScript("app.js");
var learningContext = loadBrowserScript("learning.js");

assert.equal(appContext.normalizeImportanceClass("Low"), "low");
assert.equal(appContext.normalizeImportanceClass(" medium "), "medium");
assert.equal(appContext.normalizeImportanceClass("HIGH"), "high");
assert.equal(appContext.normalizeImportanceClass("Critical"), "critical");
assert.equal(
  appContext.normalizeImportanceClass('critical\" onmouseover=\"alert(1)'),
  "medium"
);
assert.equal(appContext.normalizeImportanceClass("unexpected-class another-class"), "medium");
assert.equal(appContext.normalizeImportanceClass("__proto__"), "medium");
assert.equal(appContext.normalizeImportanceClass("constructor"), "medium");

assert.equal(learningContext.normalizeComparisonResult("match"), "match");
assert.equal(
  learningContext.normalizeComparisonResult(" partial_match "),
  "partial_match"
);
assert.equal(learningContext.normalizeComparisonResult("MISMATCH"), "mismatch");
assert.equal(
  learningContext.normalizeComparisonResult('match\" onmouseover=\"alert(1)'),
  null
);
assert.equal(learningContext.normalizeComparisonResult("unknown extra-class"), null);
assert.equal(learningContext.normalizeComparisonResult("__proto__"), null);
assert.equal(learningContext.normalizeComparisonResult("constructor"), null);

var atlasSource = fs.readFileSync("atlas-learning-engine.js", "utf8");
assert.equal(
  /console\.log\s*\(/.test(atlasSource),
  false,
  "Atlas learning engine must not log prediction or outcome records"
);

console.log("Security regression checks passed.");
