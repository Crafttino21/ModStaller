// Die Vorgaenge, die man von mehreren Stellen aus starten kann.

import { ask, chooseDevice, onDevice, runTask, toast } from "./state.svelte";
import { call } from "./rpc";
import { t } from "./i18n.svelte";
import type {
  Account, App, DeviceCheck, FixResult, InstallChoice, InstallOutcome, JitResult, PairableTv, UsbSetupResult,
} from "./types";

/** Mehr braucht es nicht, um eine App anzusprechen - so gehen auch die
 *  Eintraege fremder Werkzeuge durch dieselben Vorgaenge. */
type NamedApp = Pick<App, "bundleId" | "name">;

/** ``choice``: was der Editor geaendert hat (Name, Icon, Bundle-ID, welche
 *  Extensions bleiben, eine freie App-ID) und mit welchem Account. */
export function installIpa(path: string, name: string, choice: InstallChoice = {}) {
  runTask<InstallOutcome>("install", t("Install {name}", { name }), "install",
    onDevice({ path, ...choice }),
    (o) => ({
      message: t("{name} is installed and runs for {days} days.",
                 { name: o.name, days: Math.round(o.daysValid) }),
      notes: [
        t("Bundle ID {id} · transport: {transport}",
          { id: o.bundleId, transport: o.transport }),
        ...(o.strippedExtensions ? [t("App extensions were removed to save App IDs.")] : []),
        ...(o.newAppIds ? [t("{count} new App ID(s) created.", { count: o.newAppIds })] : []),
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
  runTask<JitResult>("jit", t("JIT for {name}", { name: app.name }), "jit", onDevice({ bundleId: app.bundleId }),
    (r) => r.preparedRegions || r.txm === false
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
      ? t("The app and its data are deleted from the device. It comes from another tool – ModStaller cannot restore it.")
      : t("The app and its data are deleted from the device. That frees one of the three slots."),
    confirm: t("Remove"),
    danger: true,
  });
  if (!ok) return;
  runTask<{ transport: string }>("uninstall", t("Remove {name}", { name: app.name }), "uninstall",
    onDevice({ bundleId: app.bundleId }),
    () => ({ message: t("{name} was removed from the device.", { name: app.name }) }));
}

/** WLAN fuer ein iPhone ein- (braucht einmal das Kabel) oder ausschalten. */
export function setWifi(udid: string, on: boolean) {
  runTask<{ udid: string; tunnel?: boolean }>("fix", on ? t("Switch on Wi-Fi") : t("Switch off Wi-Fi"),
    "device.wifi", { udid, enable: on },
    (r) => on
      ? {
          message: t("Wi-Fi is on. The iPhone can now be unplugged – ModStaller finds it in the same network."),
          notes: r.tunnel ? [] : [t("JIT and the Developer Disk Image still need the cable on this iOS version (Wi-Fi needs iOS 17.4 or newer for that).")],
        }
      : { message: t("Wi-Fi is off. The iPhone is only reachable over the cable again.") });
}

/** Ein Apple TV (per PIN - das Backend fragt ueber "prompt.pin") oder eine
 *  Vision Pro (Bestaetigung am Geraet) koppeln. */
export function pairTv(tv: PairableTv) {
  runTask<{ udid: string; name: string; osVersion: string }>("fix", t("Pair {name}", { name: tv.name }),
    "pair.start", { identifier: tv.identifier, host: tv.host, port: tv.port, name: tv.name },
    (r) => {
      chooseDevice(r.udid);
      return {
        message: t("{name} is paired.", { name: r.name || tv.name }),
        notes: [tv.kind === "vision"
          ? t("Next: turn on Developer Mode on the Vision Pro (Settings › Privacy & Security), then install an app.")
          : t("Next: turn on Developer Mode on the Apple TV (Settings › Privacy & Security), then install the tvOS version of an app.")],
      };
    });
}

/** Ein Geraet vergessen: WLAN-Kopplung, Apple-TV-Kopplung, alles Gemerkte. */
export async function forgetDevice(udid: string, name: string) {
  const { ok } = await ask({
    title: t("Forget {name}?", { name }),
    text: t("ModStaller forgets the device and its pairing. Over the cable it shows up again; an Apple TV has to be paired again with a PIN."),
    confirm: t("Forget"),
    danger: true,
  });
  if (!ok) return false;
  await call("device.forget", { udid });
  toast(t("Device forgotten."));
  return true;
}

/** ``last``: der letzte angemeldete Account - nur dann laesst sich die
 *  Geraeteidentitaet verwerfen, die alle Accounts teilen. */
export async function logout(account: Account, last: boolean) {
  const { ok, option } = await ask({
    title: t("Sign out?"),
    text: (account.appleId ? account.appleId + "\n\n" : "")
      + t("The session is discarded. Installed apps keep running but can only be renewed after signing in again."),
    confirm: t("Sign out"),
    option: last
      ? t("Also discard the device identity (Apple will then ask for a two-factor code again)")
      : undefined,
  });
  if (!ok) return false;
  await call("logout", { account: account.adsid, forgetDevice: last && option });
  toast(t("Signed out."));
  return true;
}

/** Windows: Apple-Geraetedienst installieren (Apple Devices per winget, sonst
 *  nur Apples Treiber) oder den gestoppten Dienst starten - modstaller/winsetup.py. */
export function setupUsbService() {
  runTask<UsbSetupResult>("fix", t("Set up the Apple device service"), "usb.setup", {},
    (r) => ({
      message: r.message,
      notes: r.method === "already" ? [] : [t("Unplug the iPhone and plug it in again.")],
    }));
}

export function fixCheck(check: DeviceCheck) {
  if (!check.fix) return;
  runTask<FixResult>("fix", `${check.label}: ${check.fix_label}`, "device.fix", onDevice({ fix: check.fix }),
    (r) => ({
      message: r.message,
      notes: r.manual ? [t("Still to do: {what}", { what: r.manual })] : [],
      tone: r.manual ? "warn" : "ok",
    }));
}
