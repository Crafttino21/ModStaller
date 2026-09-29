// node --test electron/daemon-i18n.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
const { DICT, t, left, resolve } = require("./daemon-i18n.cjs");

test("every language has every text, with the same placeholders", () => {
  const keys = Object.keys(DICT.de);
  const holders = (s) => (s.match(/\{\w+\}/g) ?? []).sort().join();
  for (const [lang, dict] of Object.entries(DICT)) {
    assert.deepEqual(Object.keys(dict).sort(), [...keys].sort(), lang);
    for (const key of keys) assert.equal(holders(dict[key]), holders(key), `${lang}: ${key}`);
  }
});

test("unknown languages and texts stay English", () => {
  assert.equal(t(null, "Quit"), "Quit");
  assert.equal(t("ja", "Quit"), "Quit");
  assert.equal(t("de", "Not in the dictionary"), "Not in the dictionary");
  assert.equal(resolve("de-AT"), "de");
  assert.equal(resolve("pt"), "pt-BR");
});

test("placeholders are filled in", () => {
  assert.equal(t("de", "{name} renewed", { name: "Delta" }), "Delta erneuert");
});

test("time left: days, then hours, then expired", () => {
  const H = 3600 * 1000;
  assert.equal(left("en", 3 * 24 * H + H), "3 days");
  assert.equal(left("en", 2 * 24 * H - 60 * 1000), "2 days");
  assert.equal(left("en", 10 * H - 60 * 1000), "10 hours");
  assert.equal(left("en", 24 * H), "1 day");
  assert.equal(left("de", 5 * H), "5 Stunden");
  assert.equal(left("en", 10 * 60 * 1000), "1 hour");
  assert.equal(left("de", -1), "abgelaufen");
});
