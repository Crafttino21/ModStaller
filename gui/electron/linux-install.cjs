// Linux: die Setup-AppImage installiert ModStaller fest ins Benutzerprofil.
//
// Die Setup-AppImage ist dieselbe App wie die portable, nur mit
// modstallerVariant = "setup" in package.json. Installiert wird ihr eigener
// Inhalt (das AppDir): kopiert nach ~/.local/share/modstaller-gui/app, dazu
// Starter und CLI in ~/.local/bin, Startmenue-Eintrag und Icon. Kein root,
// wie das Windows-Setup (perMachine: false).
//
// Gestartet wird die installierte Kopie ueber ihr AppRun von electron-builder:
// das findet sein Verzeichnis selbst und schaltet Chromiums Sandbox nur dort
// ab, wo sie nicht geht (z. B. Ubuntu 24.04).
//
// Nicht "~/.local/share/ModStaller": das Backend legt seine Daten unter
// ~/.local/share/modstaller ab - zwei Ordner, die sich nur in der Gross-
// schreibung unterscheiden, waeren eine Einladung zu Verwechslungen.
//
// Eigene Datei ohne Electron, damit sich alles mit `node --test` pruefen laesst.

const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

// Unter Electron das ungepatchte fs: das normale behandelt app.asar als
// Ordner - die Kopie bricht dann mit "Invalid package ... app.asar" ab.
// Unter reinem Node (Tests) gibt es original-fs nicht, da tut es node:fs.
const fs = (() => {
  try {
    return require("original-fs");
  } catch {
    return require("node:fs");
  }
})();
const fsp = fs.promises;

/** Wie electron-builder die App nennt (desktopName, Icon, WM-Klasse). */
const APP_ID = "modstaller-gui";

/** Steht in jedem Skript, das das Setup anlegt - fremde Dateien gleichen
 *  Namens (z. B. ein per pip installiertes `modstaller`) bleiben unberuehrt. */
const MARKER = "# Angelegt vom ModStaller-Setup";

/** Wo alles hinkommt. `env` und `home` nur fuer die Tests. */
function paths({ env = process.env, home = os.homedir() } = {}) {
  const data = env.XDG_DATA_HOME || path.join(home, ".local", "share");
  const config = env.XDG_CONFIG_HOME || path.join(home, ".config");
  const cache = env.XDG_CACHE_HOME || path.join(home, ".cache");
  const state = env.XDG_STATE_HOME || path.join(home, ".local", "state");
  const root = path.join(data, APP_ID);
  const bin = path.join(home, ".local", "bin");
  return {
    root,
    app: path.join(root, "app"),
    staging: path.join(root, "app.new"),
    retired: path.join(root, "app.old"),
    manifest: path.join(root, "install.json"),
    uninstaller: path.join(root, "uninstall.sh"),
    bin,
    launcher: path.join(bin, APP_ID),
    cli: path.join(bin, "modstaller"),
    desktop: path.join(data, "applications", `${APP_ID}.desktop`),
    icon: path.join(data, "icons", "hicolor", "512x512", "apps", `${APP_ID}.png`),
    // Legt die App selbst an (autostart.cjs) - weg muss sie trotzdem mit.
    autostart: path.join(config, "autostart", `${APP_ID}.desktop`),
    // Nutzerdaten - nur beim Deinstallieren mit "auch Daten loeschen".
    userData: [
      path.join(config, "ModStaller"),     // Electron (userData)
      path.join(config, "modstaller"),     // Backend: config.toml, Anmeldungen
      path.join(data, "modstaller"),
      path.join(cache, "modstaller"),
      path.join(state, "modstaller"),
      path.join(cache, "ModStaller"),      // geladene Setup-Updates
    ],
  };
}

/** Was installiert ist - oder null. */
function readManifest(p = paths()) {
  try {
    const m = JSON.parse(fs.readFileSync(p.manifest, "utf8"));
    return typeof m?.version === "string" ? m : null;
  } catch {
    return null;
  }
}

function installedVersion(p = paths()) {
  return readManifest(p)?.version ?? null;
}

/** Laeuft dieser Prozess aus der installierten Kopie? */
function isInstalledCopy(execPath, p = paths()) {
  const rel = path.relative(p.app, execPath);
  return Boolean(rel) && !rel.startsWith("..") && !path.isAbsolute(rel)
    && readManifest(p) !== null;
}

/** Liegt ~/.local/bin im Suchpfad? Sonst findet das Terminal `modstaller` nicht. */
function binOnPath(p = paths(), envPath = process.env.PATH ?? "") {
  return envPath.split(path.delimiter).some((d) => path.resolve(d) === p.bin);
}

/** Pfad fuer eine .desktop-Datei (Exec=): in Anfuehrungszeichen, wie die
 *  Spezifikation es fuer Leerzeichen verlangt. */
function desktopQuote(s) {
  return `"${s.replace(/(["`$\\])/g, "\\$1")}"`;
}

/** Fuer Shell-Skripte: einfache Anfuehrungszeichen, sicher fuer jeden Pfad. */
function shQuote(s) {
  return `'${s.replace(/'/g, "'\\''")}'`;
}

function desktopEntry(p, { version, comment }) {
  return [
    "[Desktop Entry]",
    "Type=Application",
    "Name=ModStaller",
    `Comment=${comment}`,
    `Exec=${desktopQuote(p.launcher)} %U`,
    `TryExec=${p.launcher}`,
    `Icon=${APP_ID}`,
    `StartupWMClass=${APP_ID}`,
    "Terminal=false",
    "Categories=Utility;",
    `X-ModStaller-Version=${version}`,
    "",
  ].join("\n");
}

function launcherScript(p) {
  return [
    "#!/bin/sh",
    MARKER,
    `exec ${shQuote(path.join(p.app, "AppRun"))} "$@"`,
    "",
  ].join("\n");
}

function cliScript(p) {
  return [
    "#!/bin/sh",
    MARKER,
    `exec ${shQuote(path.join(p.app, "resources", "backend", "modstaller-backend"))} "$@"`,
    "",
  ].join("\n");
}

/** Gehoert die Datei uns (oder gibt es sie gar nicht)? */
function ours(file) {
  try {
    return fs.readFileSync(file, "utf8").includes(MARKER);
  } catch (err) {
    return err.code === "ENOENT";
  }
}

function uninstallScript(p, created) {
  const rm = created.map((f) => `rm -f -- ${shQuote(f)}`);
  return [
    "#!/bin/sh",
    MARKER,
    "# Entfernt ModStaller wieder. Anmeldungen und Einstellungen bleiben;",
    "# mit --purge werden auch sie geloescht.",
    "set -e",
    ...rm,
    `rm -f -- ${shQuote(p.autostart)}`,
    `rm -rf -- ${shQuote(p.root)}`,
    'if [ "$1" = "--purge" ]; then',
    ...p.userData.map((d) => `  rm -rf -- ${shQuote(d)}`),
    "fi",
    "command -v update-desktop-database >/dev/null 2>&1 && "
      + `update-desktop-database ${shQuote(path.dirname(p.desktop))} || true`,
    'echo "ModStaller wurde entfernt."',
    "",
  ].join("\n");
}

/** Was unter `dir` liegt, Ordner zuerst - von Hand statt readdir({recursive})
 *  und fs.cp: beide halten app.asar auch mit original-fs fuer einen Ordner. */
function walk(dir, rel = "", out = []) {
  for (const e of fs.readdirSync(path.join(dir, rel), { withFileTypes: true })) {
    const r = path.join(rel, e.name);
    if (e.isSymbolicLink()) out.push({ rel: r, kind: "link" });
    else if (e.isDirectory()) {
      out.push({ rel: r, kind: "dir" });
      walk(dir, r, out);
    } else if (e.isFile()) out.push({ rel: r, kind: "file" });
  }
  return out;
}

/** Kopiert `src` nach `dst` - Rechte bleiben, Links bleiben Links (.DirIcon
 *  und das Icon im AppDir zeigen relativ ins AppDir). */
async function copyTree(src, dst, onProgress) {
  const entries = walk(src);
  let bytes = 0;
  let total = 0;
  for (const e of entries) if (e.kind === "file") total += fs.lstatSync(path.join(src, e.rel)).size;
  await fsp.mkdir(dst, { recursive: true });
  let last = -1;
  for (const e of entries) {
    const from = path.join(src, e.rel);
    const to = path.join(dst, e.rel);
    if (e.kind === "dir") {
      await fsp.mkdir(to, { recursive: true });
    } else if (e.kind === "link") {
      await fsp.symlink(await fsp.readlink(from), to);
    } else {
      await fsp.copyFile(from, to);
      const { mode, size } = fs.lstatSync(from);
      await fsp.chmod(to, mode & 0o7777);
      bytes += size;
      const percent = Math.min(99, Math.floor((bytes / Math.max(1, total)) * 100));
      if (percent !== last) {
        last = percent;
        onProgress({ step: "copy", percent });
      }
    }
  }
  // squashfs liefert Ordner als 0700 - mkdir hat sie mit der umask angelegt.
}

function writeExecutable(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, content, { mode: 0o755 });
  fs.renameSync(tmp, file);
}

/** Aufrufe, die nur dem Desktop Bescheid geben - fehlen darf jeder. */
function refreshDesktop(p) {
  const quiet = { stdio: "ignore", timeout: 10_000 };
  spawnSync("update-desktop-database", [path.dirname(p.desktop)], quiet);
  spawnSync("gtk-update-icon-cache", ["-q", "-t", path.resolve(p.icon, "..", "..", "..")], quiet);
}

/** Der Desktop-Ordner laut xdg-user-dirs - oder ~/Desktop, falls es ihn gibt. */
function desktopDir(home = os.homedir()) {
  const r = spawnSync("xdg-user-dir", ["DESKTOP"], { encoding: "utf8", timeout: 5_000 });
  const dir = r.status === 0 ? r.stdout.trim() : path.join(home, "Desktop");
  // Ohne eigenen Desktop-Ordner zeigt xdg-user-dir auf $HOME - dann lieber nichts.
  if (!dir || path.resolve(dir) === path.resolve(home)) return null;
  return fs.existsSync(dir) ? dir : null;
}

/**
 * Installiert (oder aktualisiert, oder repariert) aus `appDir`.
 *
 * Kopiert erst nach app.new und tauscht dann: bricht die Kopie ab, bleibt
 * die bisherige Installation heil. Eine laufende alte Version stoert nicht -
 * sie haelt ihre Dateien offen, auch wenn der Ordner verschoben ist.
 */
async function install({
  appDir, version, comment = "", desktopShortcut,
  onProgress = () => {}, p = paths(), home = os.homedir(), refresh = refreshDesktop,
}) {
  if (!fs.existsSync(path.join(appDir, "AppRun"))) {
    throw new Error(`Kein AppDir: ${appDir}`);
  }
  if (path.resolve(appDir) === path.resolve(p.app)) {
    throw new Error("Die installierte Kopie kann sich nicht selbst installieren.");
  }
  fs.mkdirSync(p.root, { recursive: true });
  fs.rmSync(p.staging, { recursive: true, force: true });

  onProgress({ step: "copy", percent: 0 });
  await copyTree(appDir, p.staging, onProgress);

  onProgress({ step: "activate", percent: 100 });
  fs.rmSync(p.retired, { recursive: true, force: true });
  if (fs.existsSync(p.app)) fs.renameSync(p.app, p.retired);
  fs.renameSync(p.staging, p.app);
  fs.rmSync(p.retired, { recursive: true, force: true });

  const created = [];
  writeExecutable(p.launcher, launcherScript(p));
  created.push(p.launcher);

  // `modstaller` im Terminal - aber nie ueber eine fremde Datei hinweg.
  let cli = false;
  if (ours(p.cli)) {
    writeExecutable(p.cli, cliScript(p));
    created.push(p.cli);
    cli = true;
  }

  fs.mkdirSync(path.dirname(p.icon), { recursive: true });
  const iconSrc = path.join(p.app, "usr", "share", "icons", "hicolor", "512x512", "apps", `${APP_ID}.png`);
  if (fs.existsSync(iconSrc)) {
    fs.copyFileSync(iconSrc, p.icon);
    created.push(p.icon);
  }

  const entry = desktopEntry(p, { version, comment });
  fs.mkdirSync(path.dirname(p.desktop), { recursive: true });
  fs.writeFileSync(p.desktop, entry);
  created.push(p.desktop);

  // Verknuepfung auf dem Schreibtisch: ohne ausdrueckliche Wahl (Update) so
  // lassen, wie sie war.
  const before = readManifest(p);
  if (before?.desktopShortcut && before.files) {
    for (const f of before.files) {
      if (f.endsWith(`${APP_ID}.desktop`) && f !== p.desktop) fs.rmSync(f, { force: true });
    }
  }
  const wantShortcut = desktopShortcut ?? Boolean(before?.desktopShortcut);
  let shortcut = null;
  if (wantShortcut) {
    const dir = desktopDir(home);
    if (dir) {
      shortcut = path.join(dir, `${APP_ID}.desktop`);
      fs.writeFileSync(shortcut, entry, { mode: 0o755 });
      // GNOME/Nautilus startet sie sonst erst nach "Starten erlauben".
      spawnSync("gio", ["set", shortcut, "metadata::trusted", "true"], { stdio: "ignore", timeout: 5_000 });
      created.push(shortcut);
    }
  }

  writeExecutable(p.uninstaller, uninstallScript(p, created));
  fs.writeFileSync(p.manifest, JSON.stringify({
    version,
    installedAt: new Date().toISOString(),
    desktopShortcut: Boolean(shortcut),
    files: created,
  }, null, 2));

  refresh(p);
  onProgress({ step: "done", percent: 100 });
  return { version, cli, binOnPath: binOnPath(p), files: created };
}

/** Entfernt die Installation. Anmeldungen und Einstellungen nur mit `purge`. */
function uninstall({ purge = false, p = paths(), refresh = refreshDesktop } = {}) {
  const m = readManifest(p);
  const files = m?.files ?? [p.launcher, p.cli, p.desktop, p.icon];
  for (const f of files) {
    // Starter und CLI nur, wenn sie wirklich von uns sind.
    if ((f === p.cli || f === p.launcher) && !ours(f)) continue;
    fs.rmSync(f, { force: true });
  }
  fs.rmSync(p.autostart, { force: true });
  fs.rmSync(p.root, { recursive: true, force: true });
  if (purge) {
    for (const d of p.userData) fs.rmSync(d, { recursive: true, force: true });
  }
  refresh(p);
}

module.exports = {
  APP_ID, MARKER, paths, readManifest, installedVersion, isInstalledCopy,
  binOnPath, desktopEntry, launcherScript, install, uninstall,
};
