<script lang="ts">
  import { Languages, Check } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { LANGUAGES, locale, setLocale, t } from "../lib/i18n.svelte";
  import { applyLanguage } from "../lib/state.svelte";

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

<style>
  .pad { padding: 22px; }
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
