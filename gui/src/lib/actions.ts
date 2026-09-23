// Die Vorgaenge, die man von mehreren Stellen aus starten kann.

import { ask, runTask, toast } from "./state.svelte";
import { call } from "./rpc";
import type { App, DeviceCheck, FixResult, InstallOutcome, JitResult } from "./types";

export function installIpa(path: string, name: string, keepExtensions: boolean) {
  runTask<InstallOutcome>("install", `${name} installieren`, "install",
    { path, keepExtensions },
    (o) => ({
      message: `${o.name} ist installiert und läuft ${Math.round(o.daysValid)} Tage.`,
      notes: [
        `Bundle-ID ${o.bundleId} · Transport: ${o.transport}`,
        ...(o.strippedExtensions ? ["App-Extensions wurden entfernt, um App-IDs zu sparen."] : []),
        ...(o.daysValid < 10 ? ["Vor Ablauf in der Übersicht oder unter „Apps“ erneuern."] : []),
      ],
    }));
}

/** Ohne App: alle faelligen. */
export function refreshApps(app?: App) {
  runTask<InstallOutcome[]>("refresh",
    app ? `${app.name} erneuern` : "Fällige Apps erneuern",
    "refresh", app ? { bundleId: app.bundleId } : {},
    (list) => list.length
      ? {
          message: list.length === 1
            ? `${list[0].name} ist erneuert – wieder ${Math.round(list[0].daysValid)} Tage gültig.`
            : `${list.length} Apps erneuert.`,
        }
      : { message: "Nichts war fällig.", tone: "warn" });
}

export function enableJit(app: App) {
  runTask<JitResult>("jit", `JIT für ${app.name}`, "jit", { bundleId: app.bundleId },
    (r) => r.preparedRegions
      ? { message: r.summary, notes: [...r.notes, "Gilt nur für diesen Start – nach dem Beenden der App erneut freischalten."] }
      : {
          message: r.summary,
          tone: "warn",
          notes: [
            ...r.notes,
            "Im Programm muss während des Wartens eine Instanz gestartet werden – erst dann fragt es nach Speicher.",
          ],
        });
}

export async function uninstallApp(app: App) {
  const { ok } = await ask({
    title: `${app.name} entfernen?`,
    text: "Die App und ihre Daten werden vom iPhone gelöscht. Das macht einen der drei Plätze frei.",
    confirm: "Entfernen",
    danger: true,
  });
  if (!ok) return;
  runTask<{ transport: string }>("uninstall", `${app.name} entfernen`, "uninstall",
    { bundleId: app.bundleId },
    () => ({ message: `${app.name} wurde vom iPhone entfernt.` }));
}

export async function logout() {
  const { ok, option } = await ask({
    title: "Abmelden?",
    text: "Die Sitzung wird verworfen. Installierte Apps laufen weiter, lassen sich aber erst nach erneuter Anmeldung erneuern.",
    confirm: "Abmelden",
    option: "Auch die Geräte-Identität verwerfen (Apple fragt dann wieder nach einem 2FA-Code)",
  });
  if (!ok) return false;
  await call("logout", { forgetDevice: option });
  toast("Abgemeldet.");
  return true;
}

export function fixCheck(check: DeviceCheck) {
  if (!check.fix) return;
  runTask<FixResult>("fix", `${check.label}: ${check.fix_label}`, "device.fix", { fix: check.fix },
    (r) => ({
      message: r.message,
      notes: r.manual ? [`Noch zu tun: ${r.manual}`] : [],
      tone: r.manual ? "warn" : "ok",
    }));
}
