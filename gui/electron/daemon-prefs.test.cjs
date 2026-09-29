// node --test electron/daemon-prefs.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { DEFAULTS, readPrefs, writePrefs, sanitize } = require("./daemon-prefs.cjs");

function tmpFile() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "modstaller-daemon-"));
  return path.join(dir, "daemon.json");
}

test("without a file everything is on, with the planned lead times", () => {
  const prefs = readPrefs(tmpFile());
  assert.deepEqual(prefs, DEFAULTS);
  assert.equal(prefs.remindDaysBefore, 3);
  assert.equal(prefs.refreshHoursBefore, 24);
  assert.equal(prefs.autoRefresh && prefs.autoUpdate && prefs.autostart, true);
});

test("a broken file falls back to the defaults", () => {
  const file = tmpFile();
  fs.writeFileSync(file, "{nope");
  assert.deepEqual(readPrefs(file), DEFAULTS);
});

test("writing merges into what is saved", () => {
  const file = tmpFile();
  writePrefs(file, { autoUpdate: false });
  const next = writePrefs(file, { remindDaysBefore: 2 });
  assert.equal(next.autoUpdate, false);
  assert.equal(next.remindDaysBefore, 2);
  assert.deepEqual(readPrefs(file), next);
});

test("numbers are clamped, wrong types ignored", () => {
  const p = sanitize({ remindDaysBefore: 30, refreshHoursBefore: 1, autostart: "yes", closeToTray: 0 });
  assert.equal(p.remindDaysBefore, 6);
  assert.equal(p.refreshHoursBefore, 6);
  assert.equal(p.autostart, true);
  assert.equal(p.closeToTray, true);
  assert.equal(sanitize({ remindDaysBefore: "abc" }).remindDaysBefore, 3);
});

test("only plausible language codes are kept", () => {
  assert.equal(sanitize({ language: "pt-BR" }).language, "pt-BR");
  assert.equal(sanitize({ language: "../../etc" }).language, null);
});
