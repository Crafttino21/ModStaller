// Linux: mit der Anmeldung starten, nur im Tray (--background).
//
// Electrons app.setLoginItemSettings kann das nur unter Windows und macOS.
// Unter Linux ist es eine .desktop-Datei in ~/.config/autostart nach der
// XDG-Autostart-Spezifikation - das verstehen GNOME, KDE, XFCE & Co.
//
// Was gestartet wird, haengt davon ab, wie ModStaller installiert ist - die
// Datei wird deshalb bei jedem Start neu geschrieben: wer die AppImage
// verschiebt, hat beim naechsten Start wieder den richtigen Pfad.
//
// Eigene Datei ohne Electron, damit sich alles mit `node --test` pruefen laesst.

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const APP_ID = "modstaller-gui";
const BACKGROUND_ARG = "--background";

/** Wo der Paketmanager (AUR) den Starter hinlegt. */
const PACKAGE_LAUNCHER = "/usr/bin/modstaller-gui";

function desktopFile({ env = process.env, home = os.homedir() } = {}) {
  const config = env.XDG_CONFIG_HOME || path.join(home, ".config");
  return path.join(config, "autostart", `${APP_ID}.desktop`);
}

/**
 * Was beim Anmelden gestartet wird - oder null, wenn diese Kopie keinen
 * festen Ort hat (Entwicklung, entpackte AppImage).
 *
 * `installedLauncher`: der Starter der vom Setup installierten Kopie.
 */
function launcherPath({ env = process.env, mode, packaged, installedLauncher }) {
  if (!packaged) return null;
  if (env.MODSTALLER_PACKAGE) return PACKAGE_LAUNCHER;
  if (mode === "installed") return installedLauncher ?? null;
  return env.APPIMAGE || null;
}

/** Wie in linux-install.cjs: Exec= in Anfuehrungszeichen, wie die
 *  Spezifikation es fuer Leerzeichen verlangt. */
function desktopQuote(s) {
  return `"${s.replace(/(["`$\\])/g, "\\$1")}"`;
}

function entry(exec) {
  return [
    "[Desktop Entry]",
    "Type=Application",
    "Name=ModStaller",
    "Comment=Renews your sideloaded apps before they expire.",
    `Exec=${desktopQuote(exec)} ${BACKGROUND_ARG}`,
    `Icon=${APP_ID}`,
    "Terminal=false",
    "NoDisplay=true",
    "X-GNOME-Autostart-enabled=true",
    "",
  ].join("\n");
}

/** Legt die Datei an oder bringt sie auf den Stand. Schreibt nur, wenn sich
 *  etwas aendert. */
function enable(exec, file = desktopFile()) {
  const text = entry(exec);
  try {
    if (fs.readFileSync(file, "utf8") === text) return false;
  } catch {
    // gibt es noch nicht
  }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
  return true;
}

function disable(file = desktopFile()) {
  fs.rmSync(file, { force: true });
}

function isEnabled(file = desktopFile()) {
  return fs.existsSync(file);
}

module.exports = {
  APP_ID, BACKGROUND_ARG, PACKAGE_LAUNCHER, desktopFile, launcherPath, entry, enable, disable, isEnabled,
};
