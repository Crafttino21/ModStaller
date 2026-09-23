// Die einzige Bruecke zwischen Oberflaeche und System. Bewusst schmal: die
// Seite kann Nachrichten ans Backend schicken und welche empfangen, eine IPA
// auswaehlen - sonst nichts.
const { contextBridge, ipcRenderer, webUtils } = require("electron");

contextBridge.exposeInMainWorld("backend", {
  platform: process.platform,
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
});
