<script lang="ts">
  // Neue Version: Hinweis unten in der Seitenleiste. Laden und Neustart nur
  // auf Knopfdruck - und nie, waehrend am iPhone gerade etwas laeuft.
  import { ArrowDownToLine, RotateCw, Sparkles, LoaderCircle } from "@lucide/svelte";
  import { busy, ui } from "../lib/state.svelte";

  const u = $derived(ui.update);
</script>

{#if u.state === "available" || u.state === "downloading" || u.state === "ready"}
  <div class="update">
    <div class="head">
      <Sparkles size={15} />
      <span>Version {u.version} {u.state === "ready" ? "ist bereit" : "ist da"}</span>
    </div>
    {#if u.state === "available"}
      {#if u.notes}
        <details><summary>Was ist neu?</summary><p class="selectable">{u.notes}</p></details>
      {/if}
      <button class="btn sm primary" onclick={() => window.updates.download()}>
        <ArrowDownToLine size={14} /> Herunterladen
      </button>
    {:else if u.state === "downloading"}
      <div class="bar"><div style:width="{u.percent ?? 0}%"></div></div>
      <div class="pct"><LoaderCircle size={12} class="spin" /> {u.percent ?? 0} %</div>
    {:else}
      <button class="btn sm primary" disabled={busy()} onclick={() => window.updates.install()}
              title={busy() ? "Erst den laufenden Vorgang abwarten" : ""}>
        <RotateCw size={14} /> Neu starten
      </button>
      {#if busy()}<div class="pct">Nach dem laufenden Vorgang.</div>{/if}
    {/if}
  </div>
{/if}

<style>
  .update {
    display: grid; gap: 8px; padding: 12px; border-radius: 12px;
    border: 1px solid rgb(139 108 255 / 0.4); background: var(--accent-soft);
  }
  .head { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 600; }
  .head :global(svg) { color: var(--accent); flex: none; }
  .btn { width: 100%; }
  details { font-size: 12px; color: var(--text-2); }
  summary { cursor: pointer; }
  details p { margin-top: 6px; max-height: 140px; overflow: auto; white-space: pre-line; }
  .bar { height: 6px; border-radius: 99px; background: var(--surface-2); overflow: hidden; }
  .bar div { height: 100%; background: var(--accent-grad); transition: width 0.3s; }
  .pct { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-2); font-variant-numeric: tabular-nums; }
</style>
