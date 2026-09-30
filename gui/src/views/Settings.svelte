<script lang="ts">
  import { Languages, Check, FlaskConical, TriangleAlert, BellRing, Store as StoreIcon } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { LANGUAGES, locale, setLocale, t } from "../lib/i18n.svelte";
  import { applyLanguage, errorText, toast, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { mb } from "../lib/format";
  import type { DaemonPrefs } from "../lib/types";

  // -- Update-Kanal ----------------------------------------------------------
  let beta = $state(false);
  const updatesSupported = $derived(ui.update.state !== "unsupported");
  window.updates.getBeta().then((b) => (beta = b), () => {});

  function setBeta(on: boolean) {
    beta = on;
    window.updates.setBeta(on).catch(() => {});
  }

  // -- Hintergrund -----------------------------------------------------------
  let daemon = $state<DaemonPrefs | null>(null);
  window.daemon.getPrefs().then((p) => (daemon = p), () => {});

  function setDaemon(partial: Partial<DaemonPrefs>) {
    if (!daemon) return;
    daemon = { ...daemon, ...partial };
    window.daemon.setPrefs(partial).then((p) => (daemon = p), () => {});
  }

  /** Zahlen erst beim Verlassen des Feldes uebernehmen - der Hauptprozess
   *  begrenzt sie, das Feld zeigt danach den tatsaechlichen Wert. */
  function setNumber(key: "remindDaysBefore" | "refreshHoursBefore", value: string) {
    const n = Number(value);
    if (Number.isFinite(n)) setDaemon({ [key]: n });
  }

  // -- Store-Cache ------------------------------------------------------------
  let clearing = $state(false);

  async function clearStoreCache() {
    clearing = true;
    try {
      const r = await call<{ removedIpas: number; freedBytes: number }>("store.cache.clear");
      toast(t("{size} freed ({count} IPAs removed).", { size: mb(r.freedBytes), count: r.removedIpas }));
    } catch (err) {
      toast(errorText(err), "bad");
    } finally {
      clearing = false;
    }
  }

  function pick(code: string) {
    if (code === locale()) return;
    setLocale(code);
    // Auch das Backend spricht jetzt diese Sprache - Systemcheck, Geraete-
    // checks und Fehlermeldungen kommen sonst weiter in der alten.
    applyLanguage();
  }
</script>

<PageHeader title={t("Settings")} subtitle={t("How ModStaller behaves on this computer.")} />

<div class="card pad">
  <h2><Languages size={18} /> {t("Language")}</h2>
  <p class="muted desc">
    {t("Applies to the whole program, including the messages that come from the background service.")}
  </p>

  <div class="langs">
    {#each LANGUAGES as l (l.code)}
      <button class="lang" class:active={l.code === locale()} onclick={() => pick(l.code)}>
        <span class="name">{l.name}</span>
        <span class="code">{l.code}</span>
        {#if l.code === locale()}<Check size={16} />{/if}
      </button>
    {/each}
  </div>

  <p class="faint tiny">
    {t("Translations that are missing fall back to English.")}
  </p>
</div>

{#if daemon}
<div class="card pad">
  <h2><BellRing size={18} /> {t("Background")}</h2>
  <p class="muted desc">
    {t("ModStaller can stay in the tray, remind you before apps expire and renew them on its own. Renewing needs your iPhone connected via USB.")}
  </p>

  <label class="toggle" class:off={!daemon.autostartAvailable}>
    <input type="checkbox" checked={daemon.autostart && daemon.autostartAvailable} disabled={!daemon.autostartAvailable}
           onchange={(e) => setDaemon({ autostart: e.currentTarget.checked })} />
    <span class="switch"></span>
    <div>
      <div>{t("Start with the system")}</div>
      <div class="faint small">
        {daemon.autostartAvailable
          ? t("Starts in the tray after you log in, without a window.")
          : t("Only for installed copies and the AppImage - not in development builds.")}
      </div>
    </div>
  </label>

  <label class="toggle">
    <input type="checkbox" checked={daemon.closeToTray}
           onchange={(e) => setDaemon({ closeToTray: e.currentTarget.checked })} />
    <span class="switch"></span>
    <div>
      <div>{t("Keep running in the tray when closed")}</div>
      <div class="faint small">{t("Closing the window keeps ModStaller in the tray. Quit it from the tray icon.")}</div>
    </div>
  </label>

  <label class="toggle">
    <input type="checkbox" checked={daemon.remind}
           onchange={(e) => setDaemon({ remind: e.currentTarget.checked })} />
    <span class="switch"></span>
    <div class="grow">
      <div>{t("Remind me before apps expire")}</div>
      <div class="faint small row">
        <input class="num" type="number" min="1" max="6" value={daemon.remindDaysBefore}
               disabled={!daemon.remind}
               onchange={(e) => setNumber("remindDaysBefore", e.currentTarget.value)} />
        {t("days before expiry")}
      </div>
    </div>
  </label>

  <label class="toggle">
    <input type="checkbox" checked={daemon.autoRefresh}
           onchange={(e) => setDaemon({ autoRefresh: e.currentTarget.checked })} />
    <span class="switch"></span>
    <div class="grow">
      <div>{t("Renew apps automatically")}</div>
      <div class="faint small row">
        <input class="num" type="number" min="6" max="72" value={daemon.refreshHoursBefore}
               disabled={!daemon.autoRefresh}
               onchange={(e) => setNumber("refreshHoursBefore", e.currentTarget.value)} />
        {t("hours before expiry. If your iPhone is not connected then, ModStaller asks for it and renews as soon as it is.")}
      </div>
    </div>
  </label>

  <label class="toggle">
    <input type="checkbox" checked={daemon.storeAutoUpdate}
           onchange={(e) => setDaemon({ storeAutoUpdate: e.currentTarget.checked })} />
    <span class="switch"></span>
    <div>
      <div>{t("Update store apps while renewing")}</div>
      <div class="faint small">{t("Apps from the store are brought to the newest version of their source when they are renewed – same bundle ID, the app's data stays.")}</div>
    </div>
  </label>

  <label class="toggle" class:off={!updatesSupported}>
    <input type="checkbox" checked={daemon.autoUpdate && updatesSupported} disabled={!updatesSupported}
           onchange={(e) => setDaemon({ autoUpdate: e.currentTarget.checked })} />
    <span class="switch"></span>
    <div>
      <div>{t("Install updates automatically")}</div>
      <div class="faint small">
        {updatesSupported
          ? t("Downloads new versions and installs them while ModStaller is not in use. Afterwards it keeps running in the tray.")
          : ui.update.managedBy
            ? t("Installed through your package manager ({name}) – updates come from there.", { name: ui.update.managedBy.toUpperCase() })
            : t("Automatic updates exist only in the AppImage and in the Windows version installed with the setup.")}
      </div>
    </div>
  </label>

  {#if !daemon.trayAvailable}
    <div class="banner warn small warn-beta">
      <TriangleAlert size={16} color="var(--warn)" />
      <div class="grow">{t("No tray icon available. Reminders and renewals still work; start ModStaller again to open the window.")}</div>
    </div>
  {/if}
</div>
{/if}

<div class="card pad">
  <h2><StoreIcon size={18} /> {t("Store")}</h2>
  <p class="muted desc">
    {t("Downloaded IPAs stay so apps can be renewed later. Clearing removes pictures and every IPA no installed app needs.")}
  </p>
  <button class="btn sm cache-btn" disabled={clearing} onclick={clearStoreCache}>{t("Clear store cache")}</button>
</div>

<div class="card pad">
  <h2><FlaskConical size={18} /> {t("Updates")}</h2>
  <p class="muted desc">
    {t("Stable versions are always offered. With the beta channel, pre-release versions (-beta.x) are offered as well.")}
  </p>

  <label class="toggle" class:off={!updatesSupported}>
    <input type="checkbox" checked={beta} disabled={!updatesSupported}
           onchange={(e) => setBeta(e.currentTarget.checked)} />
    <span class="switch"></span>
    <div>
      <div>{t("Receive beta versions")}</div>
      <div class="faint small">
        {updatesSupported
          ? t("Leaving the beta channel keeps the installed beta until a newer stable version is out.")
          : ui.update.managedBy
            ? t("Installed through your package manager ({name}) – updates come from there.", { name: ui.update.managedBy.toUpperCase() })
            : t("Automatic updates exist only in the AppImage and in the Windows version installed with the setup.")}
      </div>
    </div>
  </label>

  {#if beta}
    <div class="banner warn small warn-beta">
      <TriangleAlert size={16} color="var(--warn)" />
      <div class="grow">{t("Beta versions bring new features earlier, but they can be unstable and contain bugs.")}</div>
    </div>
  {/if}
</div>

<style>
  .pad { padding: 22px; margin-bottom: 14px; }
  .toggle { display: flex; gap: 14px; align-items: flex-start; cursor: pointer; padding: 14px; margin-top: 16px;
            border-radius: 12px; border: 1px solid var(--border); }
  .toggle.off { cursor: default; opacity: 0.6; }
  .toggle input { display: none; }
  .switch { width: 38px; height: 22px; flex: none; border-radius: 99px; background: var(--border-strong); position: relative; transition: background 0.15s; margin-top: 1px; }
  .switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform 0.15s; }
  .toggle input:checked + .switch { background: var(--accent); }
  .toggle input:checked + .switch::after { transform: translateX(16px); }
  .small { font-size: 12.5px; margin-top: 2px; }
  .warn-beta { margin-top: 12px; font-size: 13px; }
  .grow { flex: 1; min-width: 0; }
  .row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .num { width: 58px; padding: 4px 8px; border-radius: 8px; border: 1px solid var(--border-strong);
         background: var(--surface-2); color: var(--text); font: inherit; font-size: 12.5px; cursor: text; }
  .num:disabled { opacity: 0.5; }
  h2 { display: flex; align-items: center; gap: 9px; font-size: 17px; }
  .desc { margin-top: 8px; font-size: 13px; max-width: 640px; }
  .langs { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
           gap: 8px; margin-top: 16px; }
  .lang { display: flex; align-items: center; gap: 10px; padding: 11px 14px;
          border-radius: 11px; border: 1px solid var(--border-strong);
          background: var(--surface-2); color: var(--text); font: inherit;
          cursor: pointer; text-align: left;
          transition: border-color 0.15s, background 0.15s; }
  .lang:hover { border-color: var(--text-3); }
  .lang.active { border-color: var(--accent); background: var(--accent-soft); }
  .name { flex: 1; min-width: 0; font-weight: 550; overflow: hidden;
          text-overflow: ellipsis; white-space: nowrap; }
  .code { font-family: var(--mono); font-size: 11.5px; color: var(--text-3); }
  .tiny { margin-top: 14px; font-size: 12px; }
  .cache-btn { margin-top: 14px; }
</style>
