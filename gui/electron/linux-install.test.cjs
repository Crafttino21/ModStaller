// node --test electron/linux-install.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
// Wie im Modul: unter Electron haelt das normale fs app.asar fuer ein Archiv.
const fs = (() => {
  try {
    return require("original-fs");
  } catch {
    return require("node:fs");
  }
})();
const os = require("node:os");
const path = require("node:path");
const inst = require("./linux-install.cjs");

/** Ein Heimatordner zum Wegwerfen - und ein AppDir, wie die AppImage es hat. */
function sandbox() {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "modstaller-install-"));
  const p = inst.paths({ env: {}, home });
  const appDir = path.join(home, "mnt");
  fs.mkdirSync(path.join(appDir, "resources", "backend"), { recursive: true });
  fs.mkdirSync(path.join(appDir, "usr", "share", "icons", "hicolor", "512x512", "apps"), { recursive: true });
  fs.writeFileSync(path.join(appDir, "AppRun"), "#!/bin/sh\n", { mode: 0o755 });
  fs.writeFileSync(path.join(appDir, "modstaller-gui"), "bin", { mode: 0o755 });
  fs.writeFileSync(path.join(appDir, "resources", "backend", "modstaller-backend"), "b", { mode: 0o755 });
  // Unter Electron haelt das normale fs das fuer einen Ordner.
  fs.writeFileSync(path.join(appDir, "resources", "app.asar"), "asar-bytes");
  fs.writeFileSync(path.join(appDir, "usr", "share", "icons", "hicolor", "512x512", "apps", "modstaller-gui.png"), "png");
  fs.symlinkSync("usr/share/icons/hicolor/512x512/apps/modstaller-gui.png", path.join(appDir, ".DirIcon"));
  return { home, p, appDir };
}

const noRefresh = () => {};

test("paths stay in the user's home and follow XDG", () => {
  const p = inst.paths({ env: { XDG_DATA_HOME: "/x/data" }, home: "/h" });
  assert.equal(p.app, "/x/data/modstaller-gui/app");
  assert.equal(p.desktop, "/x/data/applications/modstaller-gui.desktop");
  assert.equal(p.launcher, "/h/.local/bin/modstaller-gui");
  assert.equal(p.cli, "/h/.local/bin/modstaller");
  // Nicht mit dem Datenordner des Backends verwechselbar.
  assert.notEqual(path.basename(p.root).toLowerCase(), "modstaller");
});

test("install puts everything in place", async () => {
  const { p, appDir, home } = sandbox();
  const progress = [];
  const res = await inst.install({
    appDir, version: "1.2.1-beta.5", p, home, refresh: noRefresh, desktopShortcut: false,
    onProgress: (e) => progress.push(e),
  });

  assert.equal(fs.readFileSync(path.join(p.app, "modstaller-gui"), "utf8"), "bin");
  assert.equal(fs.readFileSync(path.join(p.app, "resources", "app.asar"), "utf8"), "asar-bytes");
  assert.ok(fs.statSync(path.join(p.app, "resources", "backend", "modstaller-backend")).mode & 0o100);
  assert.equal(fs.readlinkSync(path.join(p.app, ".DirIcon")),
    "usr/share/icons/hicolor/512x512/apps/modstaller-gui.png");
  assert.match(fs.readFileSync(p.launcher, "utf8"), /exec '.*\/app\/AppRun' "\$@"/);
  assert.ok(fs.statSync(p.launcher).mode & 0o100, "launcher is executable");
  assert.match(fs.readFileSync(p.cli, "utf8"), /modstaller-backend/);
  const desktop = fs.readFileSync(p.desktop, "utf8");
  assert.match(desktop, /^Exec=".*modstaller-gui" %U$/m);
  assert.match(desktop, /^Icon=modstaller-gui$/m);
  assert.match(desktop, /^StartupWMClass=modstaller-gui$/m);
  assert.equal(fs.readFileSync(p.icon, "utf8"), "png");
  assert.equal(inst.installedVersion(p), "1.2.1-beta.5");
  assert.equal(res.cli, true);
  assert.equal(progress.at(-1).step, "done");
  assert.equal(fs.existsSync(p.staging), false);
});

test("an update replaces the app and keeps nothing stale", async () => {
  const { p, appDir, home } = sandbox();
  await inst.install({ appDir, version: "1.0.0", p, home, refresh: noRefresh });
  fs.writeFileSync(path.join(p.app, "stale-file"), "x");
  fs.writeFileSync(path.join(appDir, "modstaller-gui"), "bin2");

  await inst.install({ appDir, version: "1.1.0", p, home, refresh: noRefresh });

  assert.equal(fs.readFileSync(path.join(p.app, "modstaller-gui"), "utf8"), "bin2");
  assert.equal(fs.existsSync(path.join(p.app, "stale-file")), false);
  assert.equal(fs.existsSync(p.retired), false);
  assert.equal(inst.installedVersion(p), "1.1.0");
});

test("a foreign `modstaller` in ~/.local/bin is left alone", async () => {
  const { p, appDir, home } = sandbox();
  fs.mkdirSync(p.bin, { recursive: true });
  fs.writeFileSync(p.cli, "#!/usr/bin/python3\n# pip\n");

  const res = await inst.install({ appDir, version: "1.0.0", p, home, refresh: noRefresh });
  assert.equal(res.cli, false);
  assert.equal(fs.readFileSync(p.cli, "utf8"), "#!/usr/bin/python3\n# pip\n");

  inst.uninstall({ p, refresh: noRefresh });
  assert.equal(fs.existsSync(p.cli), true, "uninstall must not remove it either");
});

test("uninstall removes the installation but keeps user data", async () => {
  const { p, appDir, home } = sandbox();
  await inst.install({ appDir, version: "1.0.0", p, home, refresh: noRefresh });
  for (const d of p.userData) fs.mkdirSync(d, { recursive: true });
  fs.mkdirSync(path.dirname(p.autostart), { recursive: true });
  fs.writeFileSync(p.autostart, "[Desktop Entry]\n");

  inst.uninstall({ p, refresh: noRefresh });
  for (const f of [p.root, p.launcher, p.cli, p.desktop, p.icon, p.autostart]) {
    assert.equal(fs.existsSync(f), false, f);
  }
  for (const d of p.userData) assert.equal(fs.existsSync(d), true, d);

  inst.uninstall({ p, purge: true, refresh: noRefresh });
  for (const d of p.userData) assert.equal(fs.existsSync(d), false, d);
});

test("the generated uninstall.sh works on its own", async () => {
  const { p, appDir, home } = sandbox();
  await inst.install({ appDir, version: "1.0.0", p, home, refresh: noRefresh });
  fs.mkdirSync(path.dirname(p.autostart), { recursive: true });
  fs.writeFileSync(p.autostart, "[Desktop Entry]\n");
  const r = require("node:child_process").spawnSync("sh", [p.uninstaller], { encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
  for (const f of [p.root, p.launcher, p.cli, p.desktop, p.icon, p.autostart]) {
    assert.equal(fs.existsSync(f), false, f);
  }
});

test("refuses what is not an AppDir, and itself", async () => {
  const { p, home } = sandbox();
  await assert.rejects(inst.install({ appDir: home, version: "1", p, home, refresh: noRefresh }),
    /Kein AppDir/);
});

test("the installed copy is recognised by its path and manifest", async () => {
  const { p, appDir, home } = sandbox();
  assert.equal(inst.isInstalledCopy(path.join(p.app, "modstaller-gui"), p), false);
  await inst.install({ appDir, version: "1.0.0", p, home, refresh: noRefresh });
  assert.equal(inst.isInstalledCopy(path.join(p.app, "modstaller-gui"), p), true);
  assert.equal(inst.isInstalledCopy(path.join(appDir, "modstaller-gui"), p), false);
});

test("~/.local/bin on PATH is detected", () => {
  const p = inst.paths({ env: {}, home: "/h" });
  assert.equal(inst.binOnPath(p, "/usr/bin:/h/.local/bin"), true);
  assert.equal(inst.binOnPath(p, "/usr/bin"), false);
});
