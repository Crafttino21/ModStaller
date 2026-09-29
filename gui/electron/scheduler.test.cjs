// node --test electron/scheduler.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
const s = require("./scheduler.cjs");
const { DEFAULTS } = require("./daemon-prefs.cjs");

const H = s.HOUR;
const D = s.DAY;
const NOW = Date.UTC(2026, 8, 29, 12);

/** Eine App, die in `inMs` ablaeuft - wie der Status des Backends sie liefert. */
function app(inMs, extra = {}) {
  return {
    bundleId: "com.example.delta.ABC", name: "Delta", udid: "U1",
    expiresAt: (NOW + inMs) / 1000, sourceMissing: false, accountReady: true,
    ...extra,
  };
}

function plan(apps, { attached = ["U1"], now = NOW, prefs = DEFAULTS, memory } = {}) {
  return s.plan({ apps, attached, now, prefs, memory });
}

test("three days before expiry there is exactly one reminder", () => {
  const a = app(3 * D - H);
  const first = plan([a]);
  assert.deepEqual(first.remind.map((x) => x.name), ["Delta"]);
  assert.deepEqual(first.refresh, []);
  // Nach einem Neustart (gespeicherter memory): nicht noch einmal.
  const again = plan([a], { memory: JSON.parse(JSON.stringify(first.memory)), now: NOW + H });
  assert.deepEqual(again.remind, []);
});

test("no separate reminder once the app is already due for renewal", () => {
  const p = plan([app(10 * H)], { attached: [] });
  assert.deepEqual(p.remind, []);
  assert.equal(p.notifyDevice, true);
  // Nach dem Erneuern gibt es fuer diesen Ablauf auch spaeter keine mehr.
  assert.equal(plan([app(9 * H)], { attached: [], memory: p.memory, now: NOW + H }).remind.length, 0);
  // Ohne automatischen Refresh ist die Erinnerung die einzige Meldung.
  assert.equal(plan([app(10 * H)], { prefs: { ...DEFAULTS, autoRefresh: false } }).remind.length, 1);
});

test("no reminder earlier than configured, none when switched off", () => {
  assert.deepEqual(plan([app(3 * D + H)]).remind, []);
  assert.deepEqual(plan([app(2 * D)], { prefs: { ...DEFAULTS, remind: false } }).remind, []);
  assert.equal(plan([app(5 * D)], { prefs: { ...DEFAULTS, remindDaysBefore: 6 } }).remind.length, 1);
});

test("after a renewal the next expiry is reminded again", () => {
  const first = plan([app(2 * D)]);
  const renewed = plan([app(7 * D)], { memory: first.memory });
  assert.deepEqual(renewed.memory.reminded, {}, "the old reminder is forgotten");
  const later = plan([app(2 * D, { expiresAt: (NOW + 7 * D) / 1000 })], {
    memory: renewed.memory, now: NOW + 5 * D,
  });
  assert.equal(later.remind.length, 1);
});

test("within the last day it renews - when the iPhone is attached", () => {
  assert.deepEqual(plan([app(24 * H + 60 * 1000)]).refresh, []);
  assert.deepEqual(plan([app(23 * H)]).refresh.map((x) => x.name), ["Delta"]);
  // Schon abgelaufen, aber noch nicht lange: auch.
  assert.equal(plan([app(-2 * H)]).refresh.length, 1);
});

test("long expired apps are left alone - probably deleted from the iPhone", () => {
  const p = plan([app(-8 * D)]);
  assert.deepEqual(p.refresh, []);
  assert.deepEqual(p.waitingForDevice, []);
});

test("auto refresh off: reminders only", () => {
  const p = plan([app(2 * H)], { prefs: { ...DEFAULTS, autoRefresh: false } });
  assert.deepEqual(p.refresh, []);
  assert.deepEqual(p.waitingForDevice, []);
  assert.deepEqual(p.blocked, []);
  assert.equal(p.remind.length, 1);
});

test("without the iPhone it waits and asks for it at most every six hours", () => {
  const first = plan([app(10 * H)], { attached: [] });
  assert.deepEqual(first.refresh, []);
  assert.equal(first.waitingForDevice.length, 1);
  assert.equal(first.notifyDevice, true);

  const soon = plan([app(9 * H)], { attached: [], memory: first.memory, now: NOW + H });
  assert.equal(soon.notifyDevice, false);
  const later = plan([app(3 * H)], { attached: [], memory: first.memory, now: NOW + 6 * H });
  assert.equal(later.notifyDevice, true);

  // Angesteckt: sofort erneuern.
  const plugged = plan([app(9 * H)], { attached: ["U1"], memory: first.memory, now: NOW + H });
  assert.equal(plugged.refresh.length, 1);
});

test("another iPhone does not count, old records without a UDID take any", () => {
  assert.equal(plan([app(H)], { attached: ["OTHER"] }).waitingForDevice.length, 1);
  assert.equal(plan([app(H, { udid: "" })], { attached: ["OTHER"] }).refresh.length, 1);
});

test("a missing IPA or account is reported once per expiry instead of retried", () => {
  const a = app(5 * H, { sourceMissing: true });
  const first = plan([a]);
  assert.deepEqual(first.refresh, []);
  assert.deepEqual(first.blocked.map((b) => b.reason), ["ipa"]);
  assert.deepEqual(plan([a], { memory: first.memory }).blocked, []);

  const b = app(5 * H, { accountReady: false });
  assert.deepEqual(plan([b]).blocked.map((x) => x.reason), ["account"]);
});

test("failures back off, and only the second one is reported", () => {
  const a = app(10 * H);
  const err = { code: -32000, message: "boom", data: { kind: "AppleAPIError", exitCode: 3 } };
  const r1 = s.onRefreshResult(s.emptyMemory(), a, err, NOW);
  assert.equal(r1.notify, null);
  assert.deepEqual(plan([a], { memory: r1.memory, now: NOW + 30 * 60 * 1000 }).refresh, []);
  assert.equal(plan([a], { memory: r1.memory, now: NOW + H }).refresh.length, 1);

  const r2 = s.onRefreshResult(r1.memory, a, err, NOW + H);
  assert.equal(r2.notify, "failed");
  const r3 = s.onRefreshResult(r2.memory, a, err, NOW + 2 * H);
  assert.equal(r3.notify, null, "not on every further attempt");
});

test("what a person has to fix is reported right away", () => {
  const a = app(10 * H);
  const r = s.onRefreshResult(s.emptyMemory(), a, { code: -32000, data: { kind: "DeveloperModeDisabled" } }, NOW);
  assert.equal(r.notify, "failed");
});

test("rate limits wait longer", () => {
  const a = app(10 * H);
  const r = s.onRefreshResult(s.emptyMemory(), a, { code: -32000, data: { kind: "AppleRateLimited" } }, NOW);
  assert.equal(r.memory.nextTryAt[a.bundleId], NOW + 2 * H);
});

test("an expired sign-in asks once and retries later; a new sign-in clears it", () => {
  const a = app(10 * H);
  const err = { code: -32000, data: { kind: "AppleError" } };
  const r1 = s.onRefreshResult(s.emptyMemory(), a, err, NOW);
  assert.equal(r1.notify, "signIn");
  const r2 = s.onRefreshResult(r1.memory, a, err, NOW + 6 * H);
  assert.equal(r2.notify, null);

  const cleared = s.forgetBackoff(r2.memory);
  assert.equal(plan([a], { memory: cleared, now: NOW + 6 * H + 1 }).refresh.length, 1);
});

test("the iPhone vanishing mid-way retries soon without a message", () => {
  const a = app(10 * H);
  const r = s.onRefreshResult(s.emptyMemory(), a, { code: -32000, data: { kind: "DeviceNotFound" } }, NOW);
  assert.equal(r.notify, null);
  assert.ok(r.memory.nextTryAt[a.bundleId] <= NOW + 5 * 60 * 1000);
});

test("cancelled is no failure; success forgets all backoff", () => {
  const a = app(10 * H);
  const c = s.onRefreshResult(s.emptyMemory(), a, { code: -32800, message: "Cancelled." }, NOW);
  assert.deepEqual(c.memory.failures, {});
  const failed = s.onRefreshResult(s.emptyMemory(), a, { code: -32000, data: { kind: "AppleAPIError" } }, NOW);
  const ok = s.onRefreshResult(failed.memory, a, null, NOW + H);
  assert.deepEqual(ok.memory.nextTryAt, {});
  assert.deepEqual(ok.memory.failures, {});
});

test("memory of apps that are gone is dropped", () => {
  const a = app(2 * D);
  const first = plan([a]);
  const failed = s.onRefreshResult(first.memory, a, { code: -32000, data: { kind: "X" } }, NOW);
  const empty = plan([], { memory: failed.memory });
  assert.deepEqual(empty.memory.reminded, {});
  assert.deepEqual(empty.memory.nextTryAt, {});
  assert.deepEqual(empty.memory.failures, {});
});

test("renew now takes everything that can be renewed unattended", () => {
  const apps = [app(5 * D), app(5 * D, { bundleId: "b", sourceMissing: true }),
    app(5 * D, { bundleId: "c", udid: "OTHER" }), app(-9 * D, { bundleId: "d" })];
  assert.deepEqual(s.manualPlan({ apps, attached: ["U1"], now: NOW }).map((a) => a.bundleId),
    ["com.example.delta.ABC"]);
});

test("next refresh and next expiry for the tray", () => {
  const apps = [app(3 * D, { bundleId: "a" }), app(2 * D, { bundleId: "b" }),
    app(D, { bundleId: "c", sourceMissing: true })];
  assert.equal(s.nextRefreshAt(apps, DEFAULTS, NOW), NOW + 2 * D - 24 * H);
  assert.equal(s.nextRefreshAt(apps, { ...DEFAULTS, autoRefresh: false }, NOW), null);
  assert.equal(s.nextExpiring(apps, NOW).bundleId, "c");
});

test("updates install only when nobody is using ModStaller or about to need it", () => {
  const base = { windowVisible: false, busy: false, unusedSeconds: 900, refreshAt: null, now: NOW };
  assert.equal(s.idleForUpdate(base), true);
  assert.equal(s.idleForUpdate({ ...base, windowVisible: true }), false);
  assert.equal(s.idleForUpdate({ ...base, busy: true }), false);
  assert.equal(s.idleForUpdate({ ...base, unusedSeconds: 60 }), false);
  assert.equal(s.idleForUpdate({ ...base, refreshAt: NOW + H }), false);
  assert.equal(s.idleForUpdate({ ...base, refreshAt: NOW + 3 * H }), true);
  // Faellig, aber das iPhone fehlt seit Tagen: das Update nicht blockieren.
  assert.equal(s.idleForUpdate({ ...base, refreshAt: NOW - 2 * D }), true);
});
