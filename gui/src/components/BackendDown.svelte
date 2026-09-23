<script lang="ts">
  import { PlugZap, RotateCcw } from "@lucide/svelte";
  import { restartBackend, ui } from "../lib/state.svelte";
</script>

<div class="wrap">
  <div class="card box">
    <div class="icon"><PlugZap size={26} /></div>
    <h1>Backend nicht erreichbar</h1>
    <p class="muted">
      Der ModStaller-Dienst im Hintergrund wurde beendet
      {#if ui.exit?.code != null}(Exit {ui.exit.code}){/if}{#if ui.exit?.reason} – {ui.exit.reason}{/if}.
    </p>
    {#if ui.exit?.stderr}
      <pre class="selectable">{ui.exit.stderr}</pre>
    {/if}
    <button class="btn primary" onclick={restartBackend}><RotateCcw size={16} /> Neu starten</button>
  </div>
</div>

<style>
  .wrap { height: 100%; display: grid; place-items: center; padding: 32px; }
  .box { width: min(640px, 100%); padding: 32px; display: grid; gap: 14px; justify-items: start; }
  .icon { width: 52px; height: 52px; border-radius: 15px; display: grid; place-items: center;
          background: var(--bad-soft); color: var(--bad); }
  pre { width: 100%; max-height: 260px; overflow: auto; margin: 0; padding: 12px 14px; border-radius: 10px;
        background: var(--bg); border: 1px solid var(--border); font-family: var(--mono); font-size: 12px; white-space: pre-wrap; }
</style>
