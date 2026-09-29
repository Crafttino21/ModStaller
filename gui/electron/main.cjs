// Electron-Hauptprozess: Fenster, Backend-Prozess, Dateidialog - und der
// Hintergrundbetrieb im Tray.
//
// Das Backend ist `modstaller serve` - dieselbe Python-Logik wie die CLI,
// ueber JSON-RPC auf stdin/stdout. Dieser Prozess reicht die Zeilen nur
// durch; das Protokoll selbst spricht die Oberflaeche (src/lib/rpc.ts).
// Ausnahme: der Hintergrundbetrieb (Erinnern, Erneuern) fragt das Backend
// selbst - mit eigenen IDs ("main:<n>"), deren Antworten hier bleiben.

const {
  app, BrowserWindow, dialog, ipcMain, Menu, Notification, nativeImage, powerMonitor, shell, Tray,
} = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
// Release-Notes kommen als HTML von GitHub - angezeigt wird reiner Text.
// Eigene Datei, damit die Umwandlung ohne Electron pruefbar ist.
const { plainNotes } = require("./notes.cjs");
const channel = require("./channel.cjs");
const langseed = require("./langseed.cjs");
const daemonPrefs = require("./daemon-prefs.cjs");
const scheduler = require("./scheduler.cjs");
const autostart = require("./autostart.cjs");
const i18n = require("./daemon-i18n.cjs");

/** Wie viel stderr wir fuer die Fehleranzeige aufheben. */
const STDERR_KEEP = 60;

/** Ab dieser Groesse faengt das Protokoll von vorn an. */
const LOG_MAX_BYTES = 1024 * 1024;

/** Wie oft nach einer neuen Version geschaut wird (zusaetzlich zum Start). */
const UPDATE_INTERVAL_MS = 4 * 60 * 60 * 1000;

/** Wie oft geprueft wird, ob ein geladenes Update jetzt still rein darf. */
const UPDATE_IDLE_CHECK_MS = 5 * 60 * 1000;

/** Hintergrundbetrieb: so oft wird nachgesehen, ob etwas ablaeuft ... */
const TICK_MS = 15 * 60 * 1000;
/** ... und so oft, solange eine faellige App auf ihr iPhone wartet. */
const TICK_WAITING_MS = 60 * 1000;

/** Nur im Tray starten, ohne Fenster - so startet der Autostart. */
const BACKGROUND = process.argv.includes(autostart.BACKGROUND_ARG);

/** RPC-Methoden, die das Geraet oder den Account belegen. Laeuft eine davon
 *  aus der Oberflaeche, wartet der Hintergrund-Refresh. */
const BUSY_METHODS = new Set([
  "install", "refresh", "uninstall", "jit", "device.fix", "usb.setup", "login",
  "appids.delete", "certs.revoke",
]);

let win = null;
let backend = null;
let updater = null;
let updateState = { state: "unsupported" };
let logFile = null;

/**
 * Was die Oberflaeche ueber das Backend wissen muss. Wird *gemerkt* und nicht
 * nur verschickt: das Backend startet vor dem Fenster, und `webContents.send`
 * puffert nicht - eine Meldung an eine noch nicht geladene Seite ist weg. Die
 * Seite fragt den Zustand deshalb beim Start selbst ab (`backend:state`).
 */
let backendState = { state: "starting" };

const WINDOWS = process.platform === "win32";

/** Wird die App gerade wirklich beendet? Sonst schliesst das X nur ins Tray. */
let quitting = false;

/**
 * Wie diese Kopie laeuft:
 *
 *   "app"        normal - Windows, portable AppImage, Entwicklung
 *   "setup"      Linux-Setup-AppImage: zeigt den Installations-Assistenten
 *   "installed"  die vom Setup installierte Kopie (~/.local/share/modstaller-gui)
 *
 * Setup und installierte Kopie sind derselbe Build (modstallerVariant =
 * "setup" in package.json, siehe "dist:setup"); die installierte laeuft nur
 * nicht mehr aus einer AppImage. MODSTALLER_MODE=setup erzwingt den
 * Assistenten zum Ausprobieren (mit MODSTALLER_SETUP_APPDIR als Quelle).
 */
function runMode() {
  if (process.platform !== "linux") return "app";
  if (process.env.MODSTALLER_MODE === "setup") return "setup";
  let variant = "";
  try {
    variant = require("../package.json").modstallerVariant ?? "";
  } catch {
    // ohne package.json: normal
  }
  if (!app.isPackaged || variant !== "setup") return "app";
  return process.env.APPIMAGE ? "setup" : "installed";
}

const MODE = runMode();

/** Eine Zeile ins Protokoll. Unter Windows hat die gepackte App keine Konsole,
 *  process.stderr geht also ins Leere - die Datei ist dort die einzige Spur. */
function log(line) {
  const text = `[${new Date().toISOString()}] ${line}\n`;
  process.stderr.write(text);
  if (!logFile) return;
  try {
    if (fs.statSync(logFile).size > LOG_MAX_BYTES) fs.truncateSync(logFile, 0);
  } catch {
    // Datei gibt es noch nicht - appendFileSync legt sie an.
  }
  try {
    fs.appendFileSync(logFile, text);
  } catch {
    logFile = null; // nicht schreibbar: einmal aufgeben statt bei jeder Zeile.
  }
}

function setupLog() {
  try {
    const dir = app.getPath("logs");
    fs.mkdirSync(dir, { recursive: true });
    logFile = path.join(dir, "main.log");
  } catch {
    logFile = null;   // kein Protokollverzeichnis - dann eben nur stderr.
  }
  log(`ModStaller ${app.getVersion()} auf ${process.platform}, gepackt: ${app.isPackaged}, Modus: ${MODE}`);
}

/** Umgebung mit `dir` vorne im Suchpfad.
 *
 *  Unter Windows heisst der Schluessel `Path`, nicht `PATH`. Ein zusaetzliches
 *  `PATH` erzeugte zwei Eintraege, und welcher dann gilt, ist nicht definiert -
 *  das mitgelieferte zsign wuerde mal gefunden und mal nicht. Also den
 *  vorhandenen Schluessel in seiner eigenen Schreibweise ergaenzen.
 */
function envWithPath(dir) {
  const env = { ...process.env };
  const key = Object.keys(env).find((k) => k.toLowerCase() === "path") ?? "PATH";
  env[key] = [dir, env[key] ?? ""].join(path.delimiter);
  return env;
}

function backendCommand() {
  if (app.isPackaged) {
    const res = process.resourcesPath;
    return {
      cmd: path.join(res, "backend", WINDOWS ? "modstaller-backend.exe" : "modstaller-backend"),
      args: ["serve"],
      // Das mitgelieferte zsign zuerst finden, ein systemweites notfalls auch.
      env: envWithPath(path.join(res, "bin")),
      windowsHide: true,
    };
  }
  const root = path.resolve(__dirname, "..", "..");
  const venv = WINDOWS
    ? path.join(root, ".venv", "Scripts", "python.exe")
    : path.join(root, ".venv", "bin", "python");
  return {
    cmd: process.env.MODSTALLER_PYTHON || (fs.existsSync(venv) ? venv : "python3"),
    args: ["-m", "modstaller", "serve"],
    cwd: root,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  };
}

function startBackend() {
  const { cmd, args, cwd, env, windowsHide } = backendCommand();
  log(`Backend starten: ${cmd} ${args.join(" ")}`);
  // windowsHide: sonst blitzt unter Windows ein Konsolenfenster auf.
  const child = spawn(cmd, args, { cwd, env, windowsHide, stdio: ["pipe", "pipe", "pipe"] });
  backend = child;
  setBackendState({ state: "starting" });
  const stderrTail = [];
  let buf = "";

  // Erst damit ist ein Start positiv bestaetigt - "kein Fehler" ist es nicht.
  child.on("spawn", () => {
    log(`Backend laeuft (PID ${child.pid}).`);
    if (backend === child) setBackendState({ state: "running", pid: child.pid });
  });

  // Ohne Listener beendet ein EPIPE auf stdin den ganzen Hauptprozess - etwa
  // im Drei-Sekunden-Fenster von stopBackend oder wenn das Backend wegbricht.
  child.stdin.on("error", (err) => log(`Backend-stdin: ${err.message}`));

  child.stdout.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    buf += chunk;
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      let msg;
      try {
        msg = JSON.parse(line);
      } catch (err) {
        log(`Backend: unlesbare Zeile: ${line.slice(0, 200)}`);
        continue;
      }
      if (routeBackendMessage(msg)) continue;
      win?.webContents.send("rpc:message", msg);
    }
  });

  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => {
    for (const line of chunk.split("\n").filter(Boolean)) {
      log(`Backend: ${line}`);
      stderrTail.push(line);
    }
    stderrTail.splice(0, Math.max(0, stderrTail.length - STDERR_KEEP));
  });

  const onGone = (code, reason) => {
    if (backend !== child) return; // bewusst ersetzt
    backend = null;
    backendGone();
    log(`Backend beendet (Code ${code}${reason ? `, ${reason}` : ""}).`);
    setBackendState({
      state: "down", code, reason, stderr: stderrTail.join("\n"),
    });
  };
  child.on("error", (err) => onGone(null, `${cmd}: ${err.message}`));
  child.on("exit", (code, signal) => onGone(code, signal ? `Signal ${signal}` : ""));
}

/** Zustand merken *und* melden - in dieser Reihenfolge. Kommt die Meldung nicht
 *  an, weil die Seite noch laedt, holt die Seite ihn sich selbst ab. */
function setBackendState(next) {
  backendState = next;
  if (next.state === "down") win?.webContents.send("backend:exit", next);
}

function stopBackend() {
  const child = backend;
  backend = null;
  backendGone();
  if (!child) return;
  // stdin schliessen laesst den Server laufende Arbeit sauber abbrechen.
  child.stdin.end();
  setTimeout(() => child.exitCode === null && child.kill("SIGTERM"), 3000).unref();
}

function createWindow({ language = null, setup = null } = {}) {
  // Beides kommt als Argument ins Fenster: preload.cjs liest es synchron,
  // bevor die Oberflaeche ihre Sprache festlegt.
  const extra = [];
  if (language) extra.push(`${langseed.ARG}${language}`);
  if (setup) extra.push("--ms-mode=setup", ...(setup.update ? ["--ms-setup-update"] : []));
  win = new BrowserWindow({
    ...(setup
      ? { width: 760, height: 600, minWidth: 640, minHeight: 520, resizable: true }
      : { width: 1180, height: 780, minWidth: 880, minHeight: 600 }),
    title: setup ? "ModStaller Setup" : "ModStaller",
    backgroundColor: "#0e0f14",
    autoHideMenuBar: true,
    icon: path.join(__dirname, "..", "build", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      additionalArguments: extra,
    },
  });

  // Nur eigene Inhalte. Links nach aussen gehen in den Browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e) => e.preventDefault());

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) win.loadURL(setup ? `${devUrl}?setup=1` : devUrl);
  else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"),
      setup ? { query: { setup: "1" } } : {});
  }

  // Schliessen legt die App ins Tray, statt sie zu beenden - dort erneuert
  // sie weiter. Beenden geht ueber das Tray-Menue.
  win.on("close", (e) => {
    if (setup || quitting || !tray || !prefs().closeToTray) return;
    e.preventDefault();
    win.hide();
    trayHint();
  });
  win.on("hide", () => { hiddenSince = Date.now(); });
  win.on("show", () => { hiddenSince = null; });
  win.on("closed", () => {
    win = null;
    hiddenSince = Date.now();
  });
}

/** Das Fenster zeigen - und erst dann anlegen, wenn es noch keins gibt (im
 *  Hintergrund gestartet oder geschlossen). */
function showWindow() {
  if (!win) {
    createWindow();
    hiddenSince = null;
    return;
  }
  if (win.isMinimized()) win.restore();
  win.show();
  win.focus();
}

// -- Updates -----------------------------------------------------------------
//
// Quelle sind die GitHub-Releases (publish in electron-builder.yml). Ohne
// "Updates automatisch installieren" wird nur auf Knopfdruck geladen und
// eingespielt: ein Neustart mitten in einer Installation oder waehrend JIT
// waere fatal. Wer die App einfach schliesst, bekommt ein fertig geladenes
// Update beim Beenden eingespielt.
//
// Mit der Einstellung laedt die App selbst und spielt das Update still ein,
// sobald sie nicht benutzt wird (scheduler.idleForUpdate) - danach laeuft die
// neue Version wieder im Tray (siehe RESUME_FILE).

function setUpdateState(next) {
  updateState = {
    ...next,
    current: app.getVersion(),
    beta: betaChannel(),
    prerelease: channel.isPrerelease(next.version),
  };
  win?.webContents.send("update:state", updateState);
}

// Beta-Kanal: Betas (-beta.x) zusaetzlich zu den stabilen Versionen.
function prefsFile() {
  return path.join(app.getPath("userData"), "updates.json");
}

function betaChannel() {
  return channel.readPrefs(prefsFile(), app.getVersion()).beta;
}

function applyChannel(autoUpdater) {
  Object.assign(autoUpdater, channel.updaterFlags({ beta: betaChannel() }));
}


/** Kann diese Installation sich selbst ersetzen? */
function canSelfUpdate() {
  if (!app.isPackaged) return false;           // Entwicklung
  if (WINDOWS) return true;                    // NSIS-Installation
  if (MODE === "installed") {                  // ueber eine neue Setup-AppImage
    return linuxInstall().isInstalledCopy(process.execPath);
  }
  return Boolean(process.env.APPIMAGE);        // nur die AppImage, nicht entpackt
}

function setupUpdates() {
  // Aus einem Paket installiert (AUR: /usr/bin/modstaller-gui setzt das) -
  // dann aktualisiert der Paketmanager, nicht die App selbst.
  const managedBy = process.env.MODSTALLER_PACKAGE;
  if (managedBy) {
    setUpdateState({ state: "unsupported", managedBy });
    return;
  }
  if (!canSelfUpdate()) {
    setUpdateState({ state: "unsupported" });
    return;
  }
  if (MODE === "installed") {
    updater = installedUpdater();
    const check = () => updater.checkForUpdates().catch(() => {});
    check();
    setInterval(check, UPDATE_INTERVAL_MS).unref();
    setInterval(maybeInstallUpdate, UPDATE_IDLE_CHECK_MS).unref();
    return;
  }
  const { autoUpdater } = require("electron-updater");
  updater = autoUpdater;
  autoUpdater.autoDownload = prefs().autoUpdate;
  autoUpdater.autoInstallOnAppQuit = true;
  // Vor dem ersten Check - sonst entscheidet die Bibliothek nach der
  // laufenden Version selbst.
  applyChannel(autoUpdater);

  let version = null;
  autoUpdater.on("checking-for-update", () => setUpdateState({ state: "checking" }));
  autoUpdater.on("update-not-available", () => setUpdateState({ state: "none" }));
  autoUpdater.on("update-available", (info) => {
    version = info.version;
    setUpdateState({ state: "available", version, notes: plainNotes(info.releaseNotes) });
  });
  autoUpdater.on("download-progress", (p) =>
    setUpdateState({ state: "downloading", version, percent: Math.round(p.percent) }));
  autoUpdater.on("update-downloaded", (info) => {
    autoUpdater.autoInstallOnAppQuit = true;
    setUpdateState({ state: "ready", version: info.version });
  });
  autoUpdater.on("error", (err) =>
    setUpdateState({ state: "error", version, message: String(err?.message ?? err).split("\n")[0] }));

  const check = () => autoUpdater.checkForUpdates().catch(() => {});
  check();
  setInterval(check, UPDATE_INTERVAL_MS).unref();
  setInterval(maybeInstallUpdate, UPDATE_IDLE_CHECK_MS).unref();
}

/** Ob sich diese Installation selbst aktualisiert (und nicht der Paketmanager). */
function selfUpdating() {
  return Boolean(updater) && !process.env.MODSTALLER_PACKAGE;
}

/** Ein fertig geladenes Update still einspielen, wenn gerade niemand
 *  ModStaller benutzt. Danach startet die neue Version im Tray. */
function maybeInstallUpdate() {
  if (!selfUpdating() || !prefs().autoUpdate || updateState.state !== "ready") return;
  const now = Date.now();
  const windowVisible = Boolean(win?.isVisible());
  const idle = scheduler.idleForUpdate({
    windowVisible,
    busy: busy(),
    unusedSeconds: windowVisible || hiddenSince === null ? 0 : (now - hiddenSince) / 1000,
    refreshAt: scheduler.nextRefreshAt(lastStatus?.apps ?? [], prefs(), now),
    now,
  });
  if (!idle) return;
  log(`Update: ${updateState.version} wird still eingespielt.`);
  writeResumeMarker();
  quitting = true;
  // isSilent=true: NSIS ohne Assistent. isForceRunAfter=true: danach startet
  // die neue Version - und findet die Marke, also im Tray.
  updater.quitAndInstall(true, true);
}

// -- Updates der installierten Linux-Variante ----------------------------------
//
// Dieselbe Schnittstelle wie electron-updaters autoUpdater (checkForUpdates,
// downloadUpdate, quitAndInstall), damit die IPC-Handler und die Oberflaeche
// nichts davon merken. Eingespielt wird mit der neuen Setup-AppImage.

function linuxInstall() {
  return require("./linux-install.cjs");
}

function updateCacheDir() {
  const cache = process.env.XDG_CACHE_HOME || path.join(app.getPath("home"), ".cache");
  return path.join(cache, "ModStaller", "updates");
}

/** Startet eine Setup-AppImage losgeloest von diesem Prozess. */
function spawnSetup(file, args) {
  const env = { ...process.env };
  // Nichts von unserem eigenen AppRun an das neue Setup vererben.
  for (const key of ["APPDIR", "APPIMAGE", "ARGV0", "OWD", "LD_LIBRARY_PATH"]) delete env[key];
  const child = spawn(file, args, { detached: true, stdio: "ignore", env });
  child.unref();
}

function installedUpdater() {
  const setupUpdate = require("./setup-update.cjs");
  let found = null;
  let downloaded = null;
  const self = {
    autoInstallOnAppQuit: true,
    async checkForUpdates() {
      setUpdateState({ state: "checking" });
      try {
        found = await setupUpdate.check({ current: app.getVersion(), beta: betaChannel() });
      } catch (err) {
        setUpdateState({ state: "error", message: String(err?.message ?? err).split("\n")[0] });
        return;
      }
      if (!found) {
        setUpdateState({ state: "none" });
        return;
      }
      if (downloaded?.version === found.version) {
        setUpdateState({ state: "ready", version: found.version });
        return;
      }
      setUpdateState({ state: "available", version: found.version, notes: plainNotes(found.notes) });
      // Wie autoDownload bei electron-updater.
      if (prefs().autoUpdate) await self.downloadUpdate();
    },
    async downloadUpdate() {
      if (!found) return;
      const version = found.version;
      try {
        setUpdateState({ state: "downloading", version, percent: 0 });
        const file = await setupUpdate.download(found, {
          dir: updateCacheDir(),
          onProgress: (percent) => setUpdateState({ state: "downloading", version, percent }),
        });
        downloaded = { version, file };
        self.autoInstallOnAppQuit = true;
        setUpdateState({ state: "ready", version });
      } catch (err) {
        setUpdateState({ state: "error", version, message: String(err?.message ?? err).split("\n")[0] });
      }
    },
    quitAndInstall(silent = false) {
      if (!downloaded) return;
      // Still: ohne Setup-Fenster, danach im Tray (siehe --silent unten).
      const args = silent ? ["--update", "--silent"] : ["--update"];
      log(`Update: starte ${downloaded.file} ${args.join(" ")}`);
      spawnSetup(downloaded.file, args);
      downloaded = null;   // nicht beim Beenden ein zweites Mal
      app.quit();
    },
    /** Wer die App mit fertig geladenem Update schliesst, bekommt es auch so. */
    installOnQuit() {
      if (!downloaded || !self.autoInstallOnAppQuit) return;
      log(`Update beim Beenden: ${downloaded.file} --update --no-launch`);
      spawnSetup(downloaded.file, ["--update", "--no-launch"]);
      downloaded = null;
    },
  };
  return self;
}

ipcMain.handle("update:get", () => updateState);
ipcMain.handle("update:check", () => updater?.checkForUpdates().catch(() => {}));
ipcMain.handle("update:download", () => updater?.downloadUpdate().catch(() => {}));
ipcMain.handle("update:getBeta", () => betaChannel());
ipcMain.handle("update:setBeta", (_e, on) => {
  channel.writePrefs(prefsFile(), { beta: Boolean(on) });
  if (!updater) {
    setUpdateState({ ...updateState });
    return;
  }
  applyChannel(updater);
  // Eine schon geladene Beta nicht mehr heimlich beim Beenden einspielen.
  if (!on && updateState.state === "ready" && channel.isPrerelease(updateState.version)) {
    updater.autoInstallOnAppQuit = false;
  }
  return updater.checkForUpdates().catch(() => {});
});
ipcMain.handle("update:install", () => {
  // isSilent=false, isForceRunAfter=true: danach startet die neue Version.
  updater?.quitAndInstall(false, true);
});

// -- Hintergrundbetrieb ----------------------------------------------------------
//
// Tray, Autostart, Erinnerungen und automatischer Refresh. Was wann faellig
// ist, entscheidet scheduler.cjs; hier wird nur ausgefuehrt und gemeldet.

let tray = null;
/** Seit wann das Fenster zu ist (ms) - null, solange es offen ist. */
let hiddenSince = Date.now();
/** Der letzte Status des Backends (fuer Tray und Update-Zeitpunkt). */
let lastStatus = null;
/** Laeuft gerade ein Refresh aus dem Hintergrund: {bundleId, name}. */
let refreshing = null;
let backendReady = false;
let tickTimer = null;
let ticking = false;
let prefsCache = null;
let memory = null;

// Eigene Anfragen ans Backend. String-IDs, damit sie nie mit denen der
// Oberflaeche (Zahlen ab 1) zusammenstossen.
let mainSeq = 1;
const mainPending = new Map();
/** Laufende Anfragen der Oberflaeche, die Geraet oder Account belegen. */
const rendererJobs = new Map();
/** Benachrichtigungen festhalten - sonst raeumt der GC sie weg, bevor jemand
 *  darauf klickt (Windows). */
const liveNotifications = new Set();

function prefsFileDaemon() {
  return path.join(app.getPath("userData"), "daemon.json");
}

function memoryFile() {
  return path.join(app.getPath("userData"), "daemon-state.json");
}

/** Marke fuer "nach dem Update im Tray weiterlaufen". */
function resumeFile() {
  return path.join(app.getPath("userData"), "resume-tray.json");
}

function prefs() {
  if (!prefsCache) prefsCache = daemonPrefs.readPrefs(prefsFileDaemon());
  return prefsCache;
}

function setPrefs(partial) {
  const before = prefs();
  try {
    prefsCache = daemonPrefs.writePrefs(prefsFileDaemon(), partial);
  } catch (err) {
    log(`Hintergrund: Einstellungen nicht gespeichert: ${err.message}`);
    prefsCache = daemonPrefs.sanitize(partial, before);
  }
  return prefsCache;
}

function loadMemory() {
  try {
    return scheduler.normalizeMemory(JSON.parse(fs.readFileSync(memoryFile(), "utf8")));
  } catch {
    return scheduler.emptyMemory();
  }
}

function saveMemory() {
  try {
    fs.writeFileSync(memoryFile(), JSON.stringify(memory, null, 2));
  } catch (err) {
    log(`Hintergrund: Zustand nicht gespeichert: ${err.message}`);
  }
}

function tr(key, vars) {
  return i18n.t(prefs().language, key, vars);
}

/** Arbeitet gerade jemand mit Geraet oder Account? */
function busy() {
  return rendererJobs.size > 0 || refreshing !== null;
}

// -- Backend-Anfragen aus dem Hauptprozess --

function backendCall(method, params = {}) {
  return new Promise((resolve, reject) => {
    if (!backend) {
      reject({ code: -32603, message: "backend not running" });
      return;
    }
    const id = `main:${mainSeq++}`;
    mainPending.set(id, { resolve, reject, method });
    backend.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });
}

/**
 * Sieht jede Zeile vom Backend zuerst. true: hier erledigt, nicht an die
 * Oberflaeche weiterreichen.
 */
function routeBackendMessage(msg) {
  if (msg.method === "ready") {
    backendReady = true;
    scheduleTick(5 * 1000);
    return false;
  }
  // Rueckfrage des Backends (2FA) ohne Fenster: ablehnen, statt es ewig
  // warten zu lassen. Der Hintergrund meldet sich nie selbst an.
  if (msg.method && msg.id != null && !win) {
    backend?.stdin.write(JSON.stringify({
      jsonrpc: "2.0", id: msg.id, error: { code: -32000, message: "No window to ask." },
    }) + "\n");
    return true;
  }
  if (msg.method) return false;            // log, progress, log.entry: an die Oberflaeche

  if (typeof msg.id === "string" && msg.id.startsWith("main:")) {
    const p = mainPending.get(msg.id);
    mainPending.delete(msg.id);
    if (p) {
      if (msg.error) p.reject(msg.error);
      else p.resolve(msg.result);
    }
    return true;
  }
  const method = rendererJobs.get(msg.id);
  if (method) {
    rendererJobs.delete(msg.id);
    // Neu angemeldet: was auf die Anmeldung wartete, gleich wieder versuchen.
    if (method === "login" && !msg.error) {
      memory = scheduler.forgetBackoff(memory);
      saveMemory();
    }
    // Die Oberflaeche ist fertig - ein aufgeschobener Refresh darf jetzt.
    if (rendererJobs.size === 0) scheduleTick(10 * 1000);
  }
  return false;
}

/** Das Backend ist weg: eigene offene Anfragen scheitern. */
function backendGone() {
  backendReady = false;
  for (const [id, p] of mainPending) {
    p.reject({ code: -32603, message: "backend stopped" });
    mainPending.delete(id);
  }
  rendererJobs.clear();
}

/** Was die Oberflaeche ans Backend schickt - einmal mitlesen. */
function watchRendererMessage(msg) {
  if (!msg || typeof msg !== "object" || msg.id == null) return;
  if (BUSY_METHODS.has(msg.method)) rendererJobs.set(msg.id, msg.method);
  // Die Sprache der Oberflaeche - auch fuer Benachrichtigungen und Tray.
  if (msg.method === "i18n.set" && typeof msg.params?.language === "string"
      && msg.params.language !== prefs().language) {
    setPrefs({ language: msg.params.language });
    updateTray();
  }
}

// -- Benachrichtigungen --

function iconPath() {
  return path.join(__dirname, "..", "build", "icon.png");
}

function notify(title, body) {
  log(`Hinweis: ${title} - ${body}`);
  if (!Notification.isSupported()) return;
  const n = new Notification({ title, body, icon: iconPath() });
  liveNotifications.add(n);
  n.on("click", () => showWindow());
  n.on("close", () => liveNotifications.delete(n));
  n.show();
  // Nicht ewig festhalten, falls "close" nie kommt.
  setTimeout(() => liveNotifications.delete(n), 10 * 60 * 1000).unref();
}

/** Einmal erklaeren, dass das X nur ins Tray legt. */
function trayHint() {
  if (memory.trayHintShown) return;
  memory.trayHintShown = true;
  saveMemory();
  notify(tr("ModStaller keeps running"),
    tr("It renews your apps in the background. Quit it from the tray icon."));
}

function errorText(err) {
  return String(err?.message ?? err).split("\n")[0];
}

// -- Tray --

function createTray() {
  if (tray) return;
  try {
    let image = nativeImage.createFromPath(iconPath());
    if (!image.isEmpty()) image = image.resize({ width: WINDOWS ? 32 : 24, quality: "best" });
    tray = new Tray(image);
  } catch (err) {
    log(`Tray nicht verfuegbar: ${err.message}`);
    tray = null;
    return;
  }
  tray.setToolTip("ModStaller");
  tray.on("click", () => showWindow());
  updateTray();
}

function updateTray() {
  if (!tray) return;
  const now = Date.now();
  const apps = lastStatus?.apps ?? [];
  const next = scheduler.nextExpiring(apps, now);
  let line;
  if (refreshing) line = tr("Renewing {name} …", { name: refreshing.name });
  else if (next) {
    line = tr("Next: {name} - {left}", {
      name: next.name, left: i18n.left(prefs().language, next.expiresAt * 1000 - now),
    });
  } else line = tr("No apps installed");

  tray.setToolTip(`ModStaller\n${line}`);
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: line, enabled: false },
    { type: "separator" },
    { label: tr("Open ModStaller"), click: () => showWindow() },
    { label: tr("Renew now"), enabled: !busy() && backendReady, click: () => renewNow() },
    { type: "separator" },
    { label: tr("Quit"), click: () => app.quit() },
  ]));
}

// -- Erinnern und erneuern --

function scheduleTick(delay) {
  if (tickTimer) clearTimeout(tickTimer);
  tickTimer = setTimeout(tick, Math.max(1000, delay));
  tickTimer.unref?.();
}

async function tick() {
  tickTimer = null;
  if (ticking || !backendReady) {
    if (!backendReady) return;             // "ready" stoesst wieder an
    scheduleTick(TICK_WAITING_MS);
    return;
  }
  ticking = true;
  let delay = TICK_MS;
  try {
    const st = await backendCall("status");
    lastStatus = st;
    const now = Date.now();
    const p = prefs();
    const res = scheduler.plan({ apps: st.apps ?? [], attached: st.attached ?? [], now, prefs: p, memory });
    memory = res.memory;
    saveMemory();
    announce(res, now);

    if (res.refresh.length) {
      if (rendererJobs.size) delay = TICK_WAITING_MS;   // die Oberflaeche arbeitet - gleich nochmal
      else await runRefreshes(res.refresh);
    }
    if (res.waitingForDevice.length) delay = TICK_WAITING_MS;
    // Nicht verschlafen, wenn der naechste Refresh vor dem naechsten Tick faellt.
    const at = scheduler.nextRefreshAt(lastStatus?.apps ?? [], p, Date.now());
    if (at !== null && at > Date.now()) delay = Math.min(delay, at - Date.now() + 1000);
  } catch (err) {
    log(`Hintergrund: ${errorText(err)}`);
    delay = TICK_WAITING_MS * 5;
  } finally {
    ticking = false;
    updateTray();
    scheduleTick(delay);
  }
}

/** Die Benachrichtigungen, die `plan` beschlossen hat. */
function announce(res, now) {
  const p = prefs();
  const lang = p.language;
  for (const a of res.remind) {
    const left = i18n.left(lang, a.expiresAt * 1000 - now);
    const auto = p.autoRefresh && !a.sourceMissing && a.accountReady !== false;
    notify(tr("{name} expires soon", { name: a.name }), auto
      ? tr("Valid for {left}. ModStaller renews it on the last day - keep the device on USB or in the same Wi-Fi then.", { left })
      : tr("Valid for {left}. Open ModStaller to renew it.", { left }));
  }
  if (res.notifyDevice) {
    notify(tr("Device not reachable"), tr(
      "{names} must be renewed. Connect the device via USB or bring it into the same Wi-Fi - ModStaller does the rest.",
      { names: res.waitingForDevice.map((a) => a.name).join(", ") }));
  }
  for (const { app: a, reason } of res.blocked) {
    notify(tr("{name} cannot be renewed", { name: a.name }), reason === "ipa"
      ? tr("The original IPA is gone. Install the app again.")
      : tr("The Apple account is not signed in. Open ModStaller and sign in."));
  }
}

function setRefreshing(next) {
  refreshing = next;
  win?.webContents.send("daemon:state", daemonState());
  updateTray();
}

function daemonState() {
  return { refreshing };
}

/** Erneuert nacheinander. Faengt die Oberflaeche dazwischen etwas an, wartet
 *  der Rest auf den naechsten Tick. */
async function runRefreshes(apps) {
  for (const a of apps) {
    if (rendererJobs.size || !backend) break;
    setRefreshing({ bundleId: a.bundleId, name: a.name });
    log(`Hintergrund: erneuere ${a.bundleId}`);
    try {
      const [outcome] = await backendCall("refresh", { bundleId: a.bundleId });
      memory = scheduler.onRefreshResult(memory, a, null, Date.now()).memory;
      if (outcome) {
        const until = Date.now() + outcome.daysValid * scheduler.DAY;
        notify(tr("{name} renewed", { name: a.name }),
          tr("Valid until {date}.", { date: i18n.date(prefs().language, until) }));
      }
    } catch (err) {
      const r = scheduler.onRefreshResult(memory, a, err, Date.now());
      memory = r.memory;
      log(`Hintergrund: ${a.bundleId} nicht erneuert: ${errorText(err)}`);
      if (r.notify === "signIn") {
        notify(tr("Sign in again"),
          tr("Apple wants you to sign in again before {name} can be renewed.", { name: a.name }));
      } else if (r.notify === "failed") {
        notify(tr("Renewing {name} failed", { name: a.name }), errorText(err));
      }
    } finally {
      saveMemory();
      setRefreshing(null);
    }
  }
  // Neues Ablaufdatum in Tray und Oberflaeche.
  try {
    lastStatus = await backendCall("status");
  } catch {
    // dann eben beim naechsten Tick
  }
}

/** "Jetzt erneuern" im Tray: alles, was gerade geht - ohne Zeitfenster. */
async function renewNow() {
  if (busy() || !backendReady) return;
  try {
    const st = await backendCall("status");
    lastStatus = st;
    const apps = scheduler.manualPlan({ apps: st.apps ?? [], attached: st.attached ?? [], now: Date.now() });
    if (!apps.length) {
      notify(tr("Nothing to renew"), tr("No app can be renewed right now. Is the device connected via USB or in the same Wi-Fi?"));
      return;
    }
    await runRefreshes(apps);
  } catch (err) {
    log(`Hintergrund: ${errorText(err)}`);
  } finally {
    updateTray();
  }
}

// -- Autostart --

function applyAutostart() {
  if (!app.isPackaged || MODE === "setup") return;
  const on = prefs().autostart;
  try {
    if (WINDOWS) {
      // Fester Name statt der AppUserModelId - den loescht auch das NSIS-
      // Deinstallationsprogramm (build/installer.nsh).
      app.setLoginItemSettings({ openAtLogin: on, name: "ModStaller", args: [autostart.BACKGROUND_ARG] });
      return;
    }
    if (process.platform !== "linux") return;
    if (!on) {
      autostart.disable();
      return;
    }
    const exec = autostart.launcherPath({
      env: process.env, mode: MODE, packaged: app.isPackaged,
      installedLauncher: linuxInstall().paths().launcher,
    });
    if (exec && autostart.enable(exec)) log(`Autostart: ${exec}`);
  } catch (err) {
    log(`Autostart nicht eingerichtet: ${err.message}`);
  }
}

/** Kann diese Kopie mit dem System starten? */
function autostartAvailable() {
  if (!app.isPackaged || MODE === "setup") return false;
  if (WINDOWS) return true;
  if (process.platform !== "linux") return false;
  return autostart.launcherPath({
    env: process.env, mode: MODE, packaged: true, installedLauncher: linuxInstall().paths().launcher,
  }) !== null;
}

// -- Nach einem stillen Update --

function writeResumeMarker() {
  try {
    fs.writeFileSync(resumeFile(), JSON.stringify({ from: app.getVersion(), at: Date.now() }));
  } catch (err) {
    log(`Update: Marke nicht geschrieben: ${err.message}`);
  }
}

/** Gibt es eine frische Marke? Dann wurde diese Version gerade still
 *  eingespielt: im Tray bleiben und Bescheid sagen. Die Marke gilt einmal. */
function takeResumeMarker() {
  let marker = null;
  try {
    marker = JSON.parse(fs.readFileSync(resumeFile(), "utf8"));
    fs.rmSync(resumeFile(), { force: true });
  } catch {
    return null;
  }
  if (!marker || !(Date.now() - marker.at < 10 * 60 * 1000)) return null;
  return marker;
}

function applyPrefs(before, after) {
  if (before.autostart !== after.autostart) applyAutostart();
  if (updater && "autoDownload" in updater) updater.autoDownload = after.autoUpdate;
  if (after.autoUpdate && !before.autoUpdate && updateState.state === "available") {
    updater?.downloadUpdate().catch(() => {});
  }
  if (before.autoRefresh !== after.autoRefresh || before.remind !== after.remind
      || before.remindDaysBefore !== after.remindDaysBefore
      || before.refreshHoursBefore !== after.refreshHoursBefore) {
    scheduleTick(2000);
  }
}

function startDaemon() {
  memory = loadMemory();
  applyAutostart();
  createTray();
  // Nach Ruhezustand oder Sperre: Zeit ist vergangen, vielleicht steckt
  // jetzt ein iPhone. USB und Netz brauchen einen Moment.
  powerMonitor.on("resume", () => scheduleTick(30 * 1000));
  powerMonitor.on("unlock-screen", () => scheduleTick(30 * 1000));
}

ipcMain.handle("daemon:getPrefs", () => ({
  ...prefs(),
  autostartAvailable: autostartAvailable(),
  trayAvailable: Boolean(tray),
}));
ipcMain.handle("daemon:setPrefs", (_e, partial) => {
  const before = prefs();
  const after = setPrefs(partial);
  applyPrefs(before, after);
  return { ...after, autostartAvailable: autostartAvailable(), trayAvailable: Boolean(tray) };
});
ipcMain.handle("daemon:getState", () => daemonState());

// -- Backend ---------------------------------------------------------------

ipcMain.on("rpc:send", (_e, msg) => {
  watchRendererMessage(msg);
  backend?.stdin.write(JSON.stringify(msg) + "\n");
});

ipcMain.on("backend:restart", () => {
  stopBackend();
  startBackend();
});

ipcMain.handle("backend:state", () => backendState);

ipcMain.handle("app:logPath", () => logFile ?? "");

// Zeigt eine Log-Datei im Dateimanager. Bewusst eng: absoluter Pfad, Endung
// .log, muss existieren - die Seite bekommt so keinen Weg, beliebige Dateien
// anzustossen.
ipcMain.handle("app:showFile", (_e, p) => {
  if (typeof p !== "string" || !path.isAbsolute(p) || path.extname(p) !== ".log"
      || !fs.existsSync(p)) {
    throw new Error("not a log file");
  }
  shell.showItemInFolder(p);
});

ipcMain.handle("dialog:pickIpa", async () => {
  const res = await dialog.showOpenDialog(win, {
    title: "IPA auswählen",
    properties: ["openFile"],
    filters: [{ name: "iOS-App", extensions: ["ipa"] }],
  });
  return res.canceled ? null : res.filePaths[0];
});

// -- Linux-Setup (Setup-AppImage) --------------------------------------------

/** Was installiert wird: das AppDir, aus dem diese Setup-AppImage laeuft. */
function setupSource() {
  return process.env.MODSTALLER_SETUP_APPDIR
    || process.env.APPDIR
    || path.dirname(process.execPath);
}

function setupWindowOptions() {
  return {
    update: process.argv.includes("--update"),
    launch: !process.argv.includes("--no-launch"),
  };
}

/** Zum Anzeigen: das Heimatverzeichnis als ~. */
function tilde(p) {
  const home = app.getPath("home");
  return p === home || p.startsWith(home + path.sep) ? `~${p.slice(home.length)}` : p;
}

async function runSetupInstall(choice) {
  const { language, desktopShortcut } = choice ?? {};
  if (language) {
    langseed.writeSeed(path.join(app.getPath("userData"), langseed.SEED_FILE), language);
  }
  const res = await linuxInstall().install({
    appDir: setupSource(),
    version: app.getVersion(),
    comment: "Sign iOS apps with your own Apple account and install them over USB.",
    desktopShortcut: typeof desktopShortcut === "boolean" ? desktopShortcut : undefined,
    onProgress: (e) => win?.webContents.send("setup:progress", e),
  });
  log(`Setup: ${res.version} installiert (${res.files.length} Dateien).`);
  return res;
}

/** Stilles Update aus dem Hintergrund (--update --silent): kein Fenster,
 *  danach die installierte Kopie wieder im Tray starten - auch wenn es
 *  schiefging, dann eben die alte. */
async function silentSetupUpdate() {
  try {
    await runSetupInstall({});
  } catch (err) {
    log(`Setup: stilles Update fehlgeschlagen: ${err?.message ?? err}`);
    // Keine Marke: die alte Version soll nicht "aktualisiert" melden.
    fs.rmSync(resumeFile(), { force: true });
  }
  spawnSetup(linuxInstall().paths().launcher, [autostart.BACKGROUND_ARG]);
  app.quit();
}

function registerSetupIpc() {
  const inst = linuxInstall();
  const opts = setupWindowOptions();

  ipcMain.handle("setup:info", () => {
    const p = inst.paths();
    return {
      version: app.getVersion(),
      installed: inst.installedVersion(p),
      update: opts.update,
      launchAfter: opts.launch,
      paths: { app: tilde(p.app), launcher: tilde(p.launcher), cli: tilde(p.cli), desktop: tilde(p.desktop) },
      binOnPath: inst.binOnPath(p),
    };
  });

  ipcMain.handle("setup:install", (_e, choice) => runSetupInstall(choice));

  ipcMain.handle("setup:uninstall", (_e, choice) => {
    inst.uninstall({ purge: Boolean(choice?.purge) });
    log(`Setup: deinstalliert${choice?.purge ? " (mit Daten)" : ""}.`);
  });

  ipcMain.handle("setup:launch", () => {
    const { launcher } = inst.paths();
    spawnSetup(launcher, []);
    app.quit();
  });

  ipcMain.handle("setup:quit", () => app.quit());
}

// Nur eine laufende App: sonst starteten Autostart und ein Klick aufs Symbol
// zwei Backends, die sich um dasselbe iPhone streiten. Der zweite Start holt
// stattdessen das Fenster des ersten nach vorn. Das Setup ist davon
// ausgenommen - es ersetzt ja gerade die laufende Kopie.
const PRIMARY = MODE === "setup" || app.requestSingleInstanceLock();
if (!PRIMARY) {
  app.quit();
} else if (MODE !== "setup") {
  app.on("second-instance", (_e, argv) => {
    if (!argv.includes(autostart.BACKGROUND_ARG)) showWindow();
  });
}

app.whenReady().then(() => {
  if (!PRIMARY) return;
  setupLog();
  Menu.setApplicationMenu(null);
  // Ohne das zeigt Windows keine Benachrichtigungen (wie appId im Build).
  if (WINDOWS) app.setAppUserModelId("de.modstaller.app");
  if (MODE === "setup") {
    registerSetupIpc();
    if (process.argv.includes("--silent")) {
      silentSetupUpdate();
      return;
    }
    const language = langseed.takeSeed(path.join(app.getPath("userData"), langseed.SEED_FILE));
    createWindow({ language, setup: setupWindowOptions() });
    return;
  }
  // Die im Setup gewaehlte Sprache - genau einmal (siehe langseed.cjs).
  const language = langseed.takeSeed(path.join(app.getPath("userData"), langseed.SEED_FILE));
  if (language) {
    log(`Startsprache aus dem Setup: ${language}`);
    if (!prefs().language) setPrefs({ language });
  }
  const resumed = takeResumeMarker();
  startBackend();
  startDaemon();
  // Im Hintergrund kein Fenster. Ist das Tray-Symbol unsichtbar (GNOME ohne
  // AppIndicator-Erweiterung), fuehrt ein zweiter Start ins Fenster.
  if (BACKGROUND || resumed) log(`Start im Hintergrund${resumed ? ` nach Update von ${resumed.from}` : ""}.`);
  else createWindow({ language });
  setupUpdates();
  if (resumed && resumed.from !== app.getVersion()) {
    notify(tr("ModStaller updated"), tr("Now running version {version}.", { version: app.getVersion() }));
  }
});

// Ohne Tray (oder mit "Beim Schliessen im Tray bleiben" aus) beendet das
// letzte geschlossene Fenster die App wie bisher.
app.on("window-all-closed", () => {
  if (!tray || !prefs().closeToTray) app.quit();
});
app.on("before-quit", () => {
  quitting = true;
  stopBackend();
  updater?.installOnQuit?.();
});
