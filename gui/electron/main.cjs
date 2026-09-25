// Electron-Hauptprozess: Fenster, Backend-Prozess, Dateidialog.
//
// Das Backend ist `modstaller serve` - dieselbe Python-Logik wie die CLI,
// ueber JSON-RPC auf stdin/stdout. Dieser Prozess reicht die Zeilen nur
// durch; das Protokoll selbst spricht die Oberflaeche (src/lib/rpc.ts).

const { app, BrowserWindow, dialog, ipcMain, Menu, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
// Release-Notes kommen als HTML von GitHub - angezeigt wird reiner Text.
// Eigene Datei, damit die Umwandlung ohne Electron pruefbar ist.
const { plainNotes } = require("./notes.cjs");

/** Wie viel stderr wir fuer die Fehleranzeige aufheben. */
const STDERR_KEEP = 60;

/** Ab dieser Groesse faengt das Protokoll von vorn an. */
const LOG_MAX_BYTES = 1024 * 1024;

/** Wie oft nach einer neuen Version geschaut wird (zusaetzlich zum Start). */
const UPDATE_INTERVAL_MS = 4 * 60 * 60 * 1000;

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
  log(`ModStaller ${app.getVersion()} auf ${process.platform}, gepackt: ${app.isPackaged}`);
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
      try {
        win?.webContents.send("rpc:message", JSON.parse(line));
      } catch (err) {
        log(`Backend: unlesbare Zeile: ${line.slice(0, 200)}`);
      }
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
  if (!child) return;
  // stdin schliessen laesst den Server laufende Arbeit sauber abbrechen.
  child.stdin.end();
  setTimeout(() => child.exitCode === null && child.kill("SIGTERM"), 3000).unref();
}

function createWindow() {
  win = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 880,
    minHeight: 600,
    title: "ModStaller",
    backgroundColor: "#0e0f14",
    autoHideMenuBar: true,
    icon: path.join(__dirname, "..", "build", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // Nur eigene Inhalte. Links nach aussen gehen in den Browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e) => e.preventDefault());

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) win.loadURL(devUrl);
  else win.loadFile(path.join(__dirname, "..", "dist", "index.html"));

  win.on("closed", () => { win = null; });
}

// -- Updates -----------------------------------------------------------------
//
// Quelle sind die GitHub-Releases (publish in electron-builder.yml). Geladen
// und eingespielt wird nur auf Knopfdruck: ein Neustart mitten in einer
// Installation oder waehrend JIT waere fatal. Wer die App einfach schliesst,
// bekommt ein fertig geladenes Update beim Beenden eingespielt.

function setUpdateState(next) {
  updateState = { ...next, current: app.getVersion() };
  win?.webContents.send("update:state", updateState);
}


/** Kann diese Installation sich selbst ersetzen? */
function canSelfUpdate() {
  if (!app.isPackaged) return false;           // Entwicklung
  if (WINDOWS) return true;                    // NSIS-Installation
  return Boolean(process.env.APPIMAGE);        // nur die AppImage, nicht entpackt
}

function setupUpdates() {
  if (!canSelfUpdate()) {
    setUpdateState({ state: "unsupported" });
    return;
  }
  const { autoUpdater } = require("electron-updater");
  updater = autoUpdater;
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;

  let version = null;
  autoUpdater.on("checking-for-update", () => setUpdateState({ state: "checking" }));
  autoUpdater.on("update-not-available", () => setUpdateState({ state: "none" }));
  autoUpdater.on("update-available", (info) => {
    version = info.version;
    setUpdateState({ state: "available", version, notes: plainNotes(info.releaseNotes) });
  });
  autoUpdater.on("download-progress", (p) =>
    setUpdateState({ state: "downloading", version, percent: Math.round(p.percent) }));
  autoUpdater.on("update-downloaded", (info) =>
    setUpdateState({ state: "ready", version: info.version }));
  autoUpdater.on("error", (err) =>
    setUpdateState({ state: "error", version, message: String(err?.message ?? err).split("\n")[0] }));

  const check = () => autoUpdater.checkForUpdates().catch(() => {});
  check();
  setInterval(check, UPDATE_INTERVAL_MS).unref();
}

ipcMain.handle("update:get", () => updateState);
ipcMain.handle("update:check", () => updater?.checkForUpdates().catch(() => {}));
ipcMain.handle("update:download", () => updater?.downloadUpdate().catch(() => {}));
ipcMain.handle("update:install", () => {
  // isSilent=false, isForceRunAfter=true: danach startet die neue Version.
  updater?.quitAndInstall(false, true);
});

// -- Backend ---------------------------------------------------------------

ipcMain.on("rpc:send", (_e, msg) => {
  backend?.stdin.write(JSON.stringify(msg) + "\n");
});

ipcMain.on("backend:restart", () => {
  stopBackend();
  startBackend();
});

ipcMain.handle("backend:state", () => backendState);

ipcMain.handle("app:logPath", () => logFile ?? "");

ipcMain.handle("dialog:pickIpa", async () => {
  const res = await dialog.showOpenDialog(win, {
    title: "IPA auswählen",
    properties: ["openFile"],
    filters: [{ name: "iOS-App", extensions: ["ipa"] }],
  });
  return res.canceled ? null : res.filePaths[0];
});

app.whenReady().then(() => {
  setupLog();
  Menu.setApplicationMenu(null);
  startBackend();
  createWindow();
  setupUpdates();
});

app.on("window-all-closed", () => app.quit());
app.on("before-quit", stopBackend);
