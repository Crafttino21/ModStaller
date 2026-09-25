<script lang="ts">
  import { PlugZap, RotateCcw } from "@lucide/svelte";
  import { restartBackend, ui } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";

  let logPath = $state("");
  window.backend.logPath().then((p) => (logPath = p), () => {});
</script>

<div class="wrap">
  <div class="card box">
    <div class="icon"><PlugZap size={26} /></div>
    <h1>{t("Backend not reachable")}</h1>
    <p class="muted">
      {t("The ModStaller service in the background has stopped")}{#if ui.exit?.code != null} {t("(exit {code})", { code: ui.exit.code })}{/if}{#if ui.exit?.reason} – {ui.exit.reason}{/if}.
    </p>
    {#if ui.exit?.stderr}
      <pre class="selectable">{ui.exit.stderr}</pre>
    {/if}
    <button class="btn primary" onclick={restartBackend}><RotateCcw size={16} /> {t("Restart")}</button>
    {#if logPath}
      <p class="muted tiny">{t("Full log:")} <code class="selectable">{logPath}</code></p>
    {/if}
  </div>
</div>

<style>
  .wrap { height: 100%; display: grid; place-items: center; padding: 32px; }
  .box { width: min(640px, 100%); padding: 32px; display: grid; gap: 14px; justify-items: start; }
  .icon { width: 52px; height: 52px; border-radius: 15px; display: grid; place-items: center;
          background: var(--bad-soft); color: var(--bad); }
  .tiny { margin: 0; font-size: 11.5px; overflow-wrap: anywhere; }
  pre { width: 100%; max-height: 260px; overflow: auto; margin: 0; padding: 12px 14px; border-radius: 10px;
        background: var(--bg); border: 1px solid var(--border); font-family: var(--mono); font-size: 12px; white-space: pre-wrap; }
</style>
