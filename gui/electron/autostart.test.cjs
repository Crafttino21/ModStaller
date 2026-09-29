// node --test electron/autostart.test.cjs

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const autostart = require("./autostart.cjs");
const inst = require("./linux-install.cjs");

test("the file sits where XDG autostart looks for it", () => {
  assert.equal(autostart.desktopFile({ env: {}, home: "/h" }), "/h/.config/autostart/modstaller-gui.desktop");
  assert.equal(autostart.desktopFile({ env: { XDG_CONFIG_HOME: "/c" }, home: "/h" }),
    "/c/autostart/modstaller-gui.desktop");
});

test("the Linux uninstaller removes the same file", () => {
  const env = { XDG_CONFIG_HOME: "/c" };
  assert.equal(inst.paths({ env, home: "/h" }).autostart, autostart.desktopFile({ env, home: "/h" }));
});

test("what gets started depends on how ModStaller is installed", () => {
  const base = { packaged: true, installedLauncher: "/h/.local/bin/modstaller-gui" };
  assert.equal(autostart.launcherPath({ ...base, env: { MODSTALLER_PACKAGE: "pacman", APPIMAGE: "/x.AppImage" }, mode: "app" }),
    "/usr/bin/modstaller-gui");
  assert.equal(autostart.launcherPath({ ...base, env: {}, mode: "installed" }), "/h/.local/bin/modstaller-gui");
  assert.equal(autostart.launcherPath({ ...base, env: { APPIMAGE: "/dl/ModStaller.AppImage" }, mode: "app" }),
    "/dl/ModStaller.AppImage");
  // Entpackt oder in der Entwicklung: kein fester Ort.
  assert.equal(autostart.launcherPath({ ...base, env: {}, mode: "app" }), null);
  assert.equal(autostart.launcherPath({ ...base, packaged: false, env: { APPIMAGE: "/x" }, mode: "app" }), null);
});

test("the entry starts in the tray and survives spaces in the path", () => {
  const text = autostart.entry("/home/me/My Apps/ModStaller.AppImage");
  assert.match(text, /^Exec="\/home\/me\/My Apps\/ModStaller.AppImage" --background$/m);
  assert.match(text, /^X-GNOME-Autostart-enabled=true$/m);
});

test("enable is idempotent and follows a moved AppImage, disable removes it", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "modstaller-autostart-"));
  const file = path.join(dir, "autostart", "modstaller-gui.desktop");
  assert.equal(autostart.enable("/a.AppImage", file), true);
  assert.equal(autostart.enable("/a.AppImage", file), false);
  assert.equal(autostart.enable("/b.AppImage", file), true);
  assert.match(fs.readFileSync(file, "utf8"), /"\/b.AppImage"/);
  assert.equal(autostart.isEnabled(file), true);
  autostart.disable(file);
  autostart.disable(file);
  assert.equal(autostart.isEnabled(file), false);
});
