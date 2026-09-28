// node --test electron/setup-update.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const up = require("./setup-update.cjs");

function release(tag, { draft = false, yml = true } = {}) {
  const assets = [{ name: `ModStaller-Setup-${tag.slice(1)}-x86_64.AppImage`,
    browser_download_url: `https://dl/${tag}/setup.AppImage` }];
  if (yml) assets.push({ name: up.SETUP_YML, browser_download_url: `https://dl/${tag}/yml` });
  return { tag_name: tag, draft, body: `notes ${tag}`, assets };
}

const RELEASES = [
  release("v1.3.0-beta.1"),
  release("v1.2.1"),
  release("v1.2.1-beta.5"),
  release("v1.4.0", { draft: true }),
  release("v1.5.0", { yml: false }),   // ohne Setup-Variante (aelter als dieses Feature)
];

test("versions compare like SemVer", () => {
  const order = ["1.2.0", "1.2.1-beta.2", "1.2.1-beta.10", "1.2.1-rc.1", "1.2.1", "1.10.0"];
  for (let i = 0; i < order.length - 1; i++) {
    assert.ok(up.compareVersions(order[i], order[i + 1]) < 0, `${order[i]} < ${order[i + 1]}`);
    assert.ok(up.compareVersions(order[i + 1], order[i]) > 0);
  }
  assert.equal(up.compareVersions("v1.2.1", "1.2.1"), 0);
  assert.throws(() => up.compareVersions("banana", "1.0.0"));
});

test("stable channel: newest stable version", () => {
  assert.equal(up.pickRelease(RELEASES, "1.2.1-beta.4", { beta: false }).version, "1.2.1");
});

test("beta channel: newest version of all", () => {
  assert.equal(up.pickRelease(RELEASES, "1.2.1-beta.4", { beta: true }).version, "1.3.0-beta.1");
});

test("never a downgrade, drafts and releases without setup are skipped", () => {
  assert.equal(up.pickRelease(RELEASES, "1.3.0", { beta: true }), null);
  assert.equal(up.pickRelease([release("v1.4.0", { draft: true })], "1.0.0", { beta: true }), null);
});

test("the yml gives name and checksum - and only a plain file name", () => {
  const info = up.parseSetupYml([
    "version: 1.2.1",
    "files:",
    "  - url: ModStaller-Setup-1.2.1-x86_64.AppImage",
    "    sha512: abc==",
    "    size: 12",
    "path: ModStaller-Setup-1.2.1-x86_64.AppImage",
    "sha512: abc==",
  ].join("\n"));
  assert.deepEqual(info, { version: "1.2.1", name: "ModStaller-Setup-1.2.1-x86_64.AppImage",
    sha512: "abc==", size: 12 });
  assert.throws(() => up.parseSetupYml("version: 1\npath: ../../evil.AppImage\nsha512: x"),
    /Dateiname/);
  assert.throws(() => up.parseSetupYml("version: 1"), /unvollstaendig/);
});

function fakeFetch(routes) {
  return async (url) => {
    const body = routes[url];
    if (body === undefined) return { ok: false, status: 404 };
    const buf = Buffer.isBuffer(body) ? body : Buffer.from(typeof body === "string" ? body : JSON.stringify(body));
    return {
      ok: true, status: 200,
      headers: { get: (h) => (h === "content-length" ? String(buf.length) : null) },
      json: async () => JSON.parse(buf.toString()),
      text: async () => buf.toString(),
      body: (async function* () { yield buf.subarray(0, 3); yield buf.subarray(3); })(),
    };
  };
}

test("check and download: verified, executable, under its own name", async () => {
  const payload = Buffer.from("#!/bin/sh\necho setup\n");
  const sha512 = crypto.createHash("sha512").update(payload).digest("base64");
  const name = "ModStaller-Setup-1.2.1-x86_64.AppImage";
  const fetchImpl = fakeFetch({
    "https://api.github.com/repos/Crafttino21/ModStaller/releases?per_page=30": [release("v1.2.1")],
    "https://dl/v1.2.1/yml": `version: 1.2.1\nfiles:\n  - url: ${name}\n    sha512: ${sha512}\n`,
    "https://dl/v1.2.1/setup.AppImage": payload,
  });

  const update = await up.check({ current: "1.2.0", beta: false, fetchImpl });
  assert.equal(update.version, "1.2.1");
  assert.equal(update.notes, "notes v1.2.1");

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "modstaller-upd-"));
  const seen = [];
  const file = await up.download(update, { dir, fetchImpl, onProgress: (p) => seen.push(p) });
  assert.equal(file, path.join(dir, name));
  assert.deepEqual(fs.readFileSync(file), payload);
  assert.ok(fs.statSync(file).mode & 0o100);
  assert.equal(seen.at(-1), 100);
});

test("a wrong checksum leaves nothing behind that could be started", async () => {
  const name = "ModStaller-Setup-1.2.1-x86_64.AppImage";
  const fetchImpl = fakeFetch({ "https://dl/x": Buffer.from("tampered") });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "modstaller-upd-"));
  await assert.rejects(
    up.download({ url: "https://dl/x", name, sha512: "nope" }, { dir, fetchImpl }),
    /Pruefsumme/);
  assert.deepEqual(fs.readdirSync(dir), []);
});
