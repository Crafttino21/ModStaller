// Die Vorgaenge, die man von mehreren Stellen aus starten kann.

import { ask, runTask, toast } from "./state.svelte";
import { call } from "./rpc";
import { t } from "./i18n.svelte";
import type { App, DeviceCheck, FixResult, InstallOutcome, JitResult } from "./types";

/** Mehr braucht es nicht, um eine App anzusprechen - so gehen auch die
 *  Eintraege fremder Werkzeuge durch dieselben Vorgaenge. */
type NamedApp = Pick<App, "bundleId" | "name">;

export function installIpa(path: string, name: string, keepExtensions: boolean) {
  runTask<InstallOutcome>("install", t("Install {name}", { name }), "install",
    { path, keepExtensions },
    (o) => ({
      message: t("{name} is installed and runs for {days} days.",
                 { name: o.name, days: Math.round(o.daysValid) }),
      notes: [
        t("Bundle ID {id} · transport: {transport}",
          { id: o.bundleId, transport: o.transport }),
        ...(o.strippedExtensions ? [t("App extensions were removed to save App IDs.")] : []),
        ...(o.daysValid < 10 ? [t("Renew before it expires, from the overview or under “Apps”.")] : []),
      ],
    }));
}

/** Ohne App: alle faelligen. */
export function refreshApps(app?: App) {
  runTask<InstallOutcome[]>("refresh",
    app ? t("Renew {name}", { name: app.name }) : t("Renew due apps"),
    "refresh", app ? { bundleId: app.bundleId } : {},
    (list) => list.length
      ? {
          message: list.length === 1
            ? t("{name} was renewed – valid for {days} days again.",
                { name: list[0].name, days: Math.round(list[0].daysValid) })
            : t("Renewed {count} apps.", { count: list.length }),
        }
      : { message: t("Nothing was due."), tone: "warn" });
}

export function enableJit(app: NamedApp) {
  runTask<JitResult>("jit", t("JIT for {name}", { name: app.name }), "jit", { bundleId: app.bundleId },
    (r) => r.preparedRegions
      ? { message: r.summary, notes: [...r.notes, t("Applies to this launch only – unlock again after quitting the app.")] }
      : {
          message: r.summary,
          tone: "warn",
          notes: [
            ...r.notes,
            t("An instance has to be started inside the app while it waits – only then does it ask for memory."),
          ],
        });
}

export async function uninstallApp(app: NamedApp, foreign = false) {
  const { ok } = await ask({
    title: t("Remove {name}?", { name: app.name }),
    text: foreign
      ? t("The app and its data are deleted from the iPhone. It comes from another tool – ModStaller cannot restore it.")
      : t("The app and its data are deleted from the iPhone. That frees one of the three slots."),
    confirm: t("Remove"),
    danger: true,
  });
  if (!ok) return;
  runTask<{ transport: string }>("uninstall", t("Remove {name}", { name: app.name }), "uninstall",
    { bundleId: app.bundleId },
    () => ({ message: t("{name} was removed from the iPhone.", { name: app.name }) }));
}

export async function logout() {
  const { ok, option } = await ask({
    title: t("Sign out?"),
    text: t("The session is discarded. Installed apps keep running but can only be renewed after signing in again."),
    confirm: t("Sign out"),
    option: t("Also discard the device identity (Apple will then ask for a two-factor code again)"),
  });
  if (!ok) return false;
  await call("logout", { forgetDevice: option });
  toast(t("Signed out."));
  return true;
}

export function fixCheck(check: DeviceCheck) {
  if (!check.fix) return;
  runTask<FixResult>("fix", `${check.label}: ${check.fix_label}`, "device.fix", { fix: check.fix },
    (r) => ({
      message: r.message,
      notes: r.manual ? [t("Still to do: {what}", { what: r.manual })] : [],
      tone: r.manual ? "warn" : "ok",
    }));
}
