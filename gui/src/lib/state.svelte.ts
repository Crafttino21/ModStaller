// Zustand der ganzen Oberflaeche.
//
// Leitgedanke wie frueher in der TUI: erst zeigen, dann fragen. Der Status
// (iPhone, Anmeldung, Ablaufdaten) wird laufend nachgezogen, damit An- und
// Abstecken sofort sichtbar ist. Lange Arbeit (Installieren, Erneuern, JIT)
// ist eine globale "Aufgabe" - sie laeuft weiter, wenn man die Ansicht
// wechselt, und es laeuft immer hoechstens eine, weil sich zwei Vorgaenge am
// selben iPhone ohnehin in die Quere kaemen.

import { call, failAll, handle, on, onReady, RpcError, start, type Call } from "./rpc";
import { locale, t } from "./i18n.svelte";
import type { BackendExit, DaemonState, DeviceCheck, LogEntry, Status, UpdateState } from "./types";

export type View = "overview" | "install" | "apps" | "account" | "device" | "log" | "system" | "settings";
export type TaskKind = "install" | "refresh" | "jit" | "uninstall" | "fix";
export type TaskState = "running" | "done" | "error" | "cancelled";

export interface Task {
  kind: TaskKind;
  title: string;
  log: string[];
  pct: number | null;
  state: TaskState;
  message: string;
  notes: string[];
  /** "warn": erledigt, aber am iPhone fehlt noch ein Handgriff. */
  tone: "ok" | "warn";
  open: boolean;
  call: Call<unknown>;
}

export interface Confirm {
  title: string;
  text: string;
  confirm: string;
  danger?: boolean;
  /** Optionales Kontrollkaestchen, z. B. "Geraete-Identitaet verwerfen". */
  option?: string;
  resolve: (answer: { ok: boolean; option: boolean }) => void;
}

export interface Toast {
  id: number;
  tone: "ok" | "warn" | "bad";
  text: string;
}

const POLL_MS = 3000;

const DEVICE_KEY = "modstaller.device";

/** So viele Protokolleintraege haelt die Oberflaeche - wie das Backend. */
const LOG_KEEP = 1000;

export const ui = $state({
  view: "overview" as View,
  backend: "starting" as "starting" | "ready" | "down",
  exit: null as BackendExit | null,
  status: null as Status | null,
  task: null as Task | null,
  /** Offene 2FA-Rueckfrage des Backends. */
  twoFactor: null as null | ((code: string | null) => void),
  /** Fuer welche Apple-ID der Code gebraucht wird. */
  twoFactorFor: "",
  /** Offene PIN-Rueckfrage beim Koppeln eines Apple TV. */
  pin: null as null | ((pin: string | null) => void),
  /** Welches Apple TV die PIN zeigt. */
  pinFor: "",
  /** Der Dialog "Apple TV koppeln" ist offen. */
  pairingOpen: false,
  toasts: [] as Toast[],
  confirm: null as Confirm | null,
  /** Per Drag & Drop irgendwo ins Fenster gezogene IPA. */
  droppedIpa: null as string | null,
  /** Neue Version aus den GitHub-Releases (nur in der AppImage). */
  update: { state: "unsupported" } as UpdateState,
  /** Was der Hintergrund (Tray) gerade tut - etwa eine App erneuern. */
  daemon: { refreshing: null } as DaemonState,
  /** iPhone-Check: fuer welches Geraet (key) und mit welchem Ergebnis. */
  checks: {
    key: null as string | null,
    list: null as DeviceCheck[] | null,
    loading: false,
    error: "",
  },
  /** Das Protokoll: Verlauf beim Verbinden, danach live vom Backend. */
  log: { entries: [] as LogEntry[] },
  /** Das Geraet, das der Nutzer gewaehlt hat - null: das erste. */
  selectedUdid: savedDevice(),
});

// -- Geraetewahl ---------------------------------------------------------------

function savedDevice(): string | null {
  try {
    return localStorage.getItem(DEVICE_KEY);
  } catch {
    return null;
  }
}

/** Haengt das gewaehlte Geraet an die Parameter eines Aufrufs. Ohne Wahl
 *  entscheidet das Backend (das erste Geraet). */
export function onDevice<T extends object>(params: T): T & { udid?: string } {
  const udid = ui.status?.selectedUdid ?? ui.selectedUdid;
  return udid ? { ...params, udid } : params;
}

export function selectDevice(udid: string) {
  if (busy()) {
    toast(t("Another operation is already running."), "warn");
    return;
  }
  chooseDevice(udid);
  refreshStatus(true);
}

/** Merkt sich die Wahl, ohne nachzufragen - fuer das Ende eines Vorgangs,
 *  der danach den Status ohnehin neu holt (etwa das Koppeln). */
export function chooseDevice(udid: string) {
  ui.selectedUdid = udid;
  try {
    localStorage.setItem(DEVICE_KEY, udid);
  } catch {
    // Nicht speicherbar: gilt dann nur fuer diese Sitzung.
  }
  ui.checks.key = null;
  ui.checks.list = null;
}

export function go(view: View) {
  ui.view = view;
}

// -- Hinweise ----------------------------------------------------------------

let toastId = 1;

export function toast(text: string, tone: Toast["tone"] = "ok", ms = 4500) {
  const id = toastId++;
  ui.toasts.push({ id, tone, text });
  setTimeout(() => dismiss(id), ms);
}

export function dismiss(id: number) {
  const i = ui.toasts.findIndex((t) => t.id === id);
  if (i >= 0) ui.toasts.splice(i, 1);
}

export function errorText(err: unknown): string {
  if (err instanceof RpcError) return err.message;
  return err instanceof Error ? err.message : String(err);
}

export function ask(opts: Omit<Confirm, "resolve">): Promise<{ ok: boolean; option: boolean }> {
  return new Promise((resolve) => {
    ui.confirm = {
      ...opts,
      resolve: (answer) => {
        ui.confirm = null;
        resolve(answer);
      },
    };
  });
}

// -- Status ------------------------------------------------------------------

let polling = false;

export async function refreshStatus(force = false) {
  if (ui.backend !== "ready" || (polling && !force)) return;
  polling = true;
  try {
    ui.status = await call<Status>("status", { refresh: force, udid: ui.selectedUdid ?? undefined });
    autoCheck();
  } catch {
    // Beim naechsten Durchlauf erneut - ein einzelner Aussetzer ist kein Zustand.
  } finally {
    polling = false;
  }
}

setInterval(() => {
  if (document.visibilityState === "visible") refreshStatus();
}, POLL_MS);

// -- iPhone-Check -----------------------------------------------------------

/** Welches Geraet gerade dran ist - "attached", solange es sich nicht ausweist. */
function deviceKey(st: Status | null): string | null {
  if (!st?.deviceAttached) return null;
  return st.device?.udid ?? "attached";
}

/** Sobald ein (anderes) iPhone auftaucht oder sich entsperrt: einmal alles pruefen. */
function autoCheck() {
  const key = deviceKey(ui.status);
  if (key === null) {
    ui.checks.key = null;
    ui.checks.list = null;
    return;
  }
  // Waehrend eines Vorgangs nicht dazwischenfunken - der Entwicklermodus
  // z. B. startet das iPhone neu. Danach wird ohnehin neu geprueft.
  if (key !== ui.checks.key && !ui.checks.loading && !busy()) refreshChecks();
}

export async function refreshChecks() {
  ui.checks.loading = true;
  ui.checks.error = "";
  ui.checks.key = deviceKey(ui.status);
  try {
    ui.checks.list = await call<DeviceCheck[]>("device.checks", onDevice({}));
  } catch (err) {
    ui.checks.error = errorText(err);
  } finally {
    ui.checks.loading = false;
  }
}

// -- Aufgaben ----------------------------------------------------------------

export function busy(): boolean {
  // Auch ein Refresh aus dem Hintergrund belegt das iPhone.
  return ui.task?.state === "running" || ui.daemon.refreshing !== null;
}

/**
 * Startet eine lange Arbeit. `describe` macht aus dem Ergebnis den
 * Abschlusstext (und optionale Hinweise).
 */
export function runTask<T>(
  kind: TaskKind,
  title: string,
  method: string,
  params: object,
  describe: (result: T) => { message: string; notes?: string[]; tone?: "ok" | "warn" },
) {
  if (busy()) {
    toast(ui.daemon.refreshing
      ? t("{name} is being renewed in the background. Try again in a moment.", { name: ui.daemon.refreshing.name })
      : t("Another operation is already running."), "warn");
    return;
  }
  const task: Task = $state({
    kind, title, log: [], pct: null, state: "running",
    message: "", notes: [], tone: "ok", open: true,
    call: null as unknown as Call<unknown>,
  });
  task.call = start<T>(method, params, {
    onLog: (text) => task.log.push(...text.split("\n").filter((l) => l.trim())),
    onProgress: (pct) => (task.pct = pct),
  });
  ui.task = task;

  (task.call.result as Promise<T>).then(
    (result) => {
      const d = describe(result);
      task.state = "done";
      task.message = d.message;
      task.notes = d.notes ?? [];
      task.tone = d.tone ?? "ok";
      if (!task.open) toast(d.message, d.tone ?? "ok");
    },
    (err) => {
      const cancelled = err instanceof RpcError && err.cancelled;
      task.state = cancelled ? "cancelled" : "error";
      task.message = cancelled ? t("Cancelled.") : errorText(err);
      if (!task.open) toast(`${title}: ${task.message}`, cancelled ? "warn" : "bad", 8000);
    },
  ).finally(async () => {
    await refreshStatus(true);
    if (ui.status?.deviceAttached) refreshChecks();
  });
}

export function closeTask() {
  if (!ui.task) return;
  if (ui.task.state === "running") ui.task.open = false;
  else ui.task = null;
}

// -- Backend -----------------------------------------------------------------

handle("prompt.2fa", (params) => new Promise((resolve) => {
  ui.twoFactorFor = String((params as { appleId?: string } | undefined)?.appleId ?? "");
  ui.twoFactor = (code) => {
    ui.twoFactor = null;
    resolve(code);
  };
}));

handle("prompt.pin", (params) => new Promise((resolve) => {
  ui.pinFor = String((params as { name?: string } | undefined)?.name ?? "");
  ui.pin = (pin) => {
    ui.pin = null;
    resolve(pin);
  };
}));

/** Wie lange die Oberflaeche auf das erste Lebenszeichen wartet. Grosszuegig:
 *  das gepackte Backend muss beim ersten Start seine Bibliotheken auspacken. */
const BOOT_TIMEOUT_MS = 20_000;

let bootTimer: ReturnType<typeof setTimeout> | null = null;

/** Weder ein "ready" noch ein "exit"? Dann lieber sagen, dass nichts kommt,
 *  als fuer immer den Startbildschirm zu zeigen. */
function armBootTimeout() {
  if (bootTimer !== null) clearTimeout(bootTimer);
  bootTimer = setTimeout(() => {
    bootTimer = null;
    if (ui.backend === "starting") {
      markDown({ code: null, stderr: "",
                 reason: t("The backend did not report in.") });
    }
  }, BOOT_TIMEOUT_MS);
}

function stopBootTimeout() {
  if (bootTimer === null) return;
  clearTimeout(bootTimer);
  bootTimer = null;
}

function markReady() {
  stopBootTimeout();
  if (ui.backend === "ready") return;
  ui.backend = "ready";
  ui.exit = null;
  applyLanguage();
  refreshStatus(true);
  loadLog();
}

// -- Protokoll -----------------------------------------------------------------

function keepLog() {
  const extra = ui.log.entries.length - LOG_KEEP;
  if (extra > 0) ui.log.entries.splice(0, extra);
}

on("log.entry", (entry: LogEntry) => {
  ui.log.entries.push(entry);
  keepLog();
});

/** Holt, was vor dem Verbinden geschah. Ein neu gestartetes Backend zaehlt
 *  wieder ab 1 - deshalb ersetzt der Verlauf alles; nur was live schon
 *  nachkam, bleibt dahinter stehen. */
function loadLog() {
  call<LogEntry[]>("log.history").then((history) => {
    const last = history.length ? history[history.length - 1].id : 0;
    const live = ui.log.entries.filter((e) => e.id > last);
    ui.log.entries = [...history, ...live];
    keepLog();
  }, () => {});
}

/** Sagt dem Backend, in welcher Sprache es antworten soll, und holt alles
 *  neu, was von dort schon uebersetzt kam - Systemcheck und Geraetechecks
 *  haetten sonst weiter die alten Texte. */
export function applyLanguage() {
  call("i18n.set", { language: locale() }).then(() => {
    ui.checks.key = null;
    refreshStatus(true);
  }, () => {});
}

function markDown(info: BackendExit) {
  stopBootTimeout();
  if (ui.backend === "down") return;
  ui.backend = "down";
  ui.exit = info;
  ui.twoFactor = null;
  ui.pin = null;
  failAll(t("The backend has stopped."));
}

onReady(markReady);
// Das Backend startet vor dem Fenster - sein "ready" kann laengst verschickt
// sein, bevor diese Seite zuhoert. Also selbst nachfragen.
call("version").then(markReady, () => {});

// Und genauso kann sein Tod schon gemeldet worden sein, bevor es hier jemanden
// gab, der zuhoert: `webContents.send` puffert nicht. Der Hauptprozess merkt
// sich den Zustand deshalb - hier einmal abholen.
window.backend.getState().then((s) => {
  if (s?.state === "down") markDown(s);
}, () => {});

window.backend.onExit(markDown);

armBootTimeout();

export function restartBackend() {
  ui.backend = "starting";
  ui.exit = null;
  window.backend.restart();
  armBootTimeout();
}

// -- Updates -----------------------------------------------------------------

window.updates.get().then((s) => (ui.update = s));
window.updates.onState((s) => (ui.update = s));

// -- Hintergrund -------------------------------------------------------------

function applyDaemonState(s: DaemonState) {
  const finished = ui.daemon.refreshing !== null && s.refreshing === null;
  ui.daemon = s;
  // Neues Ablaufdatum gleich zeigen.
  if (finished) refreshStatus(true);
}

window.daemon.getState().then(applyDaemonState, () => {});
window.daemon.onState(applyDaemonState);
