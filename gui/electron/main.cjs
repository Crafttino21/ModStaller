// Electron-Hauptprozess: Fenster, Backend-Prozess, Dateidialog.
//
// Das Backend ist `modstaller serve` - dieselbe Python-Logik wie die CLI,
// ueber JSON-RPC auf stdin/stdout. Dieser Prozess reicht die Zeilen nur
// durch; das Protokoll selbst spricht die Oberflaeche (src/lib/rpc.ts).

const { app, BrowserWindow, dialog, ipcMain, Menu, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

/** Wie viel stderr wir fuer die Fehleranzeige aufheben. */
const STDERR_KEEP = 60;

let win = null;
let backend = null;

function backendCommand() {
  if (app.isPackaged) {
    const res = process.resourcesPath;
    return {
      cmd: path.join(res, "backend", "modstaller-backend"),
      args: ["serve"],
      // Das mitgelieferte zsign zuerst finden, ein systemweites notfalls auch.
      env: { ...process.env, PATH: `${path.join(res, "bin")}:${process.env.PATH ?? ""}` },
    };
  }
  const root = path.resolve(__dirname, "..", "..");
  const venv = path.join(root, ".venv", "bin", "python");
  return {
    cmd: process.env.MODSTALLER_PYTHON || (fs.existsSync(venv) ? venv : "python3"),
    args: ["-m", "modstaller", "serve"],
    cwd: root,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  };
}

function startBackend() {
  const { cmd, args, cwd, env } = backendCommand();
  const child = spawn(cmd, args, { cwd, env, stdio: ["pipe", "pipe", "pipe"] });
  backend = child;
  const stderrTail = [];
  let buf = "";

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
        console.error("Backend: unlesbare Zeile:", line.slice(0, 200));
      }
    }
  });

  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => {
    process.stderr.write(chunk);
    stderrTail.push(...chunk.split("\n").filter(Boolean));
    stderrTail.splice(0, Math.max(0, stderrTail.length - STDERR_KEEP));
  });

  const onGone = (code, reason) => {
    if (backend !== child) return; // bewusst ersetzt
    backend = null;
    win?.webContents.send("backend:exit", {
      code, reason, stderr: stderrTail.join("\n"),
    });
  };
  child.on("error", (err) => onGone(null, `${cmd}: ${err.message}`));
  child.on("exit", (code, signal) => onGone(code, signal ? `Signal ${signal}` : ""));
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

ipcMain.on("rpc:send", (_e, msg) => {
  backend?.stdin.write(JSON.stringify(msg) + "\n");
});

ipcMain.on("backend:restart", () => {
  stopBackend();
  startBackend();
});

ipcMain.handle("dialog:pickIpa", async () => {
  const res = await dialog.showOpenDialog(win, {
    title: "IPA auswählen",
    properties: ["openFile"],
    filters: [{ name: "iOS-App", extensions: ["ipa"] }],
  });
  return res.canceled ? null : res.filePaths[0];
});

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  startBackend();
  createWindow();
});

app.on("window-all-closed", () => app.quit());
app.on("before-quit", stopBackend);
