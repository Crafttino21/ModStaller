<script lang="ts">
  import { Languages, Check, FlaskConical, TriangleAlert } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { LANGUAGES, locale, setLocale, t } from "../lib/i18n.svelte";
  import { applyLanguage, ui } from "../lib/state.svelte";

  // -- Update-Kanal ----------------------------------------------------------
  let beta = $state(false);
  const updatesSupported = $derived(ui.update.state !== "unsupported");
  window.updates.getBeta().then((b) => (beta = b), () => {});

  function setBeta(on: boolean) {
    beta = on;
    window.updates.setBeta(on).catch(() => {});
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
</style>
