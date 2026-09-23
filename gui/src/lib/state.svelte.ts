// Zustand der ganzen Oberflaeche.
//
// Leitgedanke wie frueher in der TUI: erst zeigen, dann fragen. Der Status
// (iPhone, Anmeldung, Ablaufdaten) wird laufend nachgezogen, damit An- und
// Abstecken sofort sichtbar ist. Lange Arbeit (Installieren, Erneuern, JIT)
// ist eine globale "Aufgabe" - sie laeuft weiter, wenn man die Ansicht
// wechselt, und es laeuft immer hoechstens eine, weil sich zwei Vorgaenge am
// selben iPhone ohnehin in die Quere kaemen.

import { call, failAll, handle, onReady, RpcError, start, type Call } from "./rpc";
import type { BackendExit, DeviceCheck, Status, UpdateState } from "./types";

export type View = "overview" | "install" | "apps" | "account" | "device" | "system";
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

export const ui = $state({
  view: "overview" as View,
  backend: "starting" as "starting" | "ready" | "down",
  exit: null as BackendExit | null,
  status: null as Status | null,
  task: null as Task | null,
  /** Offene 2FA-Rueckfrage des Backends. */
  twoFactor: null as null | ((code: string | null) => void),
  toasts: [] as Toast[],
  confirm: null as Confirm | null,
  /** Per Drag & Drop irgendwo ins Fenster gezogene IPA. */
  droppedIpa: null as string | null,
  /** Neue Version aus den GitHub-Releases (nur in der AppImage). */
  update: { state: "unsupported" } as UpdateState,
  /** iPhone-Check: fuer welches Geraet (key) und mit welchem Ergebnis. */
  checks: {
    key: null as string | null,
    list: null as DeviceCheck[] | null,
    loading: false,
    error: "",
  },
});

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
    ui.status = await call<Status>("status", { refresh: force });
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
    ui.checks.list = await call<DeviceCheck[]>("device.checks");
  } catch (err) {
    ui.checks.error = errorText(err);
  } finally {
    ui.checks.loading = false;
  }
}

// -- Aufgaben ----------------------------------------------------------------

export function busy(): boolean {
  return ui.task?.state === "running";
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
    toast("Es läuft bereits ein Vorgang.", "warn");
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
      task.message = cancelled ? "Abgebrochen." : errorText(err);
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

handle("prompt.2fa", () => new Promise((resolve) => {
  ui.twoFactor = (code) => {
    ui.twoFactor = null;
    resolve(code);
  };
}));

function markReady() {
  if (ui.backend === "ready") return;
  ui.backend = "ready";
  ui.exit = null;
  refreshStatus(true);
}

onReady(markReady);
// Das Backend startet vor dem Fenster - sein "ready" kann laengst verschickt
// sein, bevor diese Seite zuhoert. Also selbst nachfragen.
call("version").then(markReady, () => {});

window.backend.onExit((info) => {
  ui.backend = "down";
  ui.exit = info;
  ui.twoFactor = null;
  failAll("Das Backend wurde beendet.");
});

export function restartBackend() {
  ui.backend = "starting";
  ui.exit = null;
  window.backend.restart();
}

// -- Updates -----------------------------------------------------------------

window.updates.get().then((s) => (ui.update = s));
window.updates.onState((s) => (ui.update = s));
