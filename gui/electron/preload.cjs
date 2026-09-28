// Die einzige Bruecke zwischen Oberflaeche und System. Bewusst schmal: die
// Seite kann Nachrichten ans Backend schicken und welche empfangen, eine IPA
// auswaehlen - sonst nichts.
const { contextBridge, ipcRenderer, webUtils } = require("electron");

// Vom Hauptprozess mitgegeben (additionalArguments): die Startsprache aus dem
// Setup und ob dieses Fenster der Linux-Installationsassistent ist.
// Kein require von langseed.cjs - im Sandbox-Preload geht nur "electron".
function arg(prefix) {
  const hit = process.argv.find((a) => a.startsWith(prefix));
  return hit ? hit.slice(prefix.length) : null;
}
const isSetup = process.argv.includes("--ms-mode=setup");

contextBridge.exposeInMainWorld("backend", {
  platform: process.platform,
  initialLanguage: arg("--ms-lang="),
  send: (msg) => ipcRenderer.send("rpc:send", msg),
  onMessage: (cb) => {
    const listener = (_e, msg) => cb(msg);
    ipcRenderer.on("rpc:message", listener);
    return () => ipcRenderer.off("rpc:message", listener);
  },
  onExit: (cb) => {
    const listener = (_e, info) => cb(info);
    ipcRenderer.on("backend:exit", listener);
    return () => ipcRenderer.off("backend:exit", listener);
  },
  // Das Backend startet vor dem Fenster: ein "backend:exit" von vorhin hat
  // diese Seite nie erreicht. Also nachfragen, statt ewig zu warten.
  getState: () => ipcRenderer.invoke("backend:state"),
  logPath: () => ipcRenderer.invoke("app:logPath"),
  // Nur Log-Dateien - die Seite soll damit keine beliebigen Pfade oeffnen.
  showFile: (p) => ipcRenderer.invoke("app:showFile", p),
  restart: () => ipcRenderer.send("backend:restart"),
  pickIpa: () => ipcRenderer.invoke("dialog:pickIpa"),
  // Seit Electron 32 hat File kein .path mehr - fuer Drag & Drop noetig.
  pathForFile: (file) => webUtils.getPathForFile(file),
});

contextBridge.exposeInMainWorld("updates", {
  get: () => ipcRenderer.invoke("update:get"),
  onState: (cb) => {
    const listener = (_e, state) => cb(state);
    ipcRenderer.on("update:state", listener);
    return () => ipcRenderer.off("update:state", listener);
  },
  check: () => ipcRenderer.invoke("update:check"),
  download: () => ipcRenderer.invoke("update:download"),
  install: () => ipcRenderer.invoke("update:install"),
  getBeta: () => ipcRenderer.invoke("update:getBeta"),
  setBeta: (on) => ipcRenderer.invoke("update:setBeta", on),
});

// Nur im Linux-Setup: installieren, deinstallieren, danach starten.
if (isSetup) {
  contextBridge.exposeInMainWorld("setup", {
    autoUpdate: process.argv.includes("--ms-setup-update"),
    info: () => ipcRenderer.invoke("setup:info"),
    install: (choice) => ipcRenderer.invoke("setup:install", choice),
    uninstall: (choice) => ipcRenderer.invoke("setup:uninstall", choice),
    launch: () => ipcRenderer.invoke("setup:launch"),
    quit: () => ipcRenderer.invoke("setup:quit"),
    onProgress: (cb) => {
      const listener = (_e, p) => cb(p);
      ipcRenderer.on("setup:progress", listener);
      return () => ipcRenderer.off("setup:progress", listener);
    },
  });
}
