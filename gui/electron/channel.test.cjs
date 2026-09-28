// node --test electron/channel.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { isPrerelease, readPrefs, writePrefs, updaterFlags } = require("./channel.cjs");

function tmpFile() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "modstaller-channel-"));
  return path.join(dir, "updates.json");
}

test("recognises beta versions", () => {
  assert.equal(isPrerelease("1.2.1-beta.3"), true);
  assert.equal(isPrerelease("1.2.0"), false);
  assert.equal(isPrerelease(undefined), false);
});

test("without a saved choice a beta stays on the beta channel", () => {
  const file = tmpFile();
  assert.deepEqual(readPrefs(file, "1.2.1-beta.3"), { beta: true });
  assert.deepEqual(readPrefs(file, "1.2.0"), { beta: false });
});

test("the saved choice wins over the running version", () => {
  const file = tmpFile();
  writePrefs(file, { beta: false });
  assert.deepEqual(readPrefs(file, "1.2.1-beta.3"), { beta: false });
  writePrefs(file, { beta: true });
  assert.deepEqual(readPrefs(file, "1.2.0"), { beta: true });
});

test("a broken file falls back to the default", () => {
  const file = tmpFile();
  fs.writeFileSync(file, "{not json");
  assert.deepEqual(readPrefs(file, "1.2.0"), { beta: false });
  fs.writeFileSync(file, JSON.stringify({ beta: "yes" }));
  assert.deepEqual(readPrefs(file, "1.2.0"), { beta: false });
});

test("leaving the beta channel never downgrades", () => {
  assert.deepEqual(updaterFlags({ beta: true }), { allowPrerelease: true, allowDowngrade: false });
  assert.deepEqual(updaterFlags({ beta: false }), { allowPrerelease: false, allowDowngrade: false });
});
