// node --test electron/langseed.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { takeSeed, writeSeed, isLanguageCode } = require("./langseed.cjs");

function tmpFile() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "modstaller-langseed-"));
  return path.join(dir, "language.json");
}

test("the setup's language is taken exactly once", () => {
  const file = tmpFile();
  fs.writeFileSync(file, '{"language":"de"}');
  assert.equal(takeSeed(file), "de");
  assert.equal(fs.existsSync(file), false);
  assert.equal(takeSeed(file), null);
});

test("without a file there is no seed", () => {
  assert.equal(takeSeed(tmpFile()), null);
});

test("a broken or foreign file is ignored - and removed", () => {
  for (const content of ["{", '{"language":42}', '{"language":"../../etc"}', "[]"]) {
    const file = tmpFile();
    fs.writeFileSync(file, content);
    assert.equal(takeSeed(file), null, content);
    assert.equal(fs.existsSync(file), false, content);
  }
});

test("region codes pass through - the interface resolves them", () => {
  assert.equal(isLanguageCode("pt-BR"), true);
  assert.equal(isLanguageCode("de"), true);
  assert.equal(isLanguageCode(""), false);
  assert.equal(isLanguageCode("de; rm -rf"), false);
});

test("the Linux setup writes what the app later takes", () => {
  const file = path.join(path.dirname(tmpFile()), "sub", "language.json");
  assert.equal(writeSeed(file, "fr"), true);
  assert.equal(takeSeed(file), "fr");
  assert.equal(writeSeed(file, "not a code"), false);
  assert.equal(fs.existsSync(file), false);
});
