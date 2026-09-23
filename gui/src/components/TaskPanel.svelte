<script lang="ts">
  import { CircleCheck, CircleX, LoaderCircle, Ban, Minimize2, Info } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { closeTask, ui } from "../lib/state.svelte";

  const task = $derived(ui.task!);
  let logEl = $state<HTMLDivElement | undefined>();

  // Neuestes immer sichtbar halten.
  $effect(() => {
    task.log.length;
    if (logEl) logEl.scrollTop = logEl.scrollHeight;
  });
</script>

<Modal width={620} onclose={closeTask}>
  <div class="head">
    <div class="state {task.state}">
      {#if task.state === "running"}
        <LoaderCircle size={22} class="spin" />
      {:else if task.state === "done"}
        <CircleCheck size={22} />
      {:else if task.state === "cancelled"}
        <Ban size={22} />
      {:else}
        <CircleX size={22} />
      {/if}
    </div>
    <div class="grow">
      <h2>{task.title}</h2>
      <p class="muted">
        {#if task.state === "running"}
          {task.log.at(-1) ?? "Wird gestartet …"}
        {:else}
          {task.state === "done" ? "Fertig" : task.state === "cancelled" ? "Abgebrochen" : "Fehlgeschlagen"}
        {/if}
      </p>
    </div>
  </div>

  {#if task.state === "running" && task.pct !== null}
    <div class="bar"><div style:width="{task.pct}%"></div></div>
    <div class="pct faint">{task.pct}% übertragen</div>
  {:else if task.state === "running"}
    <div class="bar indeterminate"><div></div></div>
  {/if}

  {#if task.kind === "jit" && task.state === "running"}
    <div class="banner info hint">
      <Info size={18} />
      <div class="grow">
        Starte jetzt in der App eine Instanz (z.&nbsp;B. ein Spiel) – erst dann fragt sie nach
        Speicher. Die Freischaltung gilt nur für diesen Start der App.
      </div>
    </div>
  {/if}

  {#if task.state !== "running" && task.message}
    <div class="result {task.state} {task.tone} selectable">{task.message}</div>
  {/if}
  {#each task.notes as note}
    <p class="note muted selectable">{note}</p>
  {/each}

  <details open={task.state === "error"}>
    <summary>Protokoll ({task.log.length})</summary>
    <div class="log selectable" bind:this={logEl}>
      {#each task.log as line}
        <div>{line}</div>
      {:else}
        <div class="faint">Noch keine Meldungen.</div>
      {/each}
    </div>
  </details>

  <div class="actions">
    {#if task.state === "running"}
      <button class="btn ghost" onclick={closeTask}><Minimize2 size={16} /> Im Hintergrund</button>
      <button class="btn danger" onclick={() => task.call.cancel()}>Abbrechen</button>
    {:else}
      <button class="btn primary" onclick={closeTask}>Schließen</button>
    {/if}
  </div>
</Modal>

<style>
  .head { display: flex; gap: 14px; align-items: flex-start; }
  .head p { margin-top: 3px; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 480px; }
  .grow { flex: 1; min-width: 0; }
  .state { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; flex: none; }
  .state.running { background: var(--accent-soft); color: var(--accent); }
  .state.done { background: var(--ok-soft); color: var(--ok); }
  .state.error { background: var(--bad-soft); color: var(--bad); }
  .state.cancelled { background: var(--warn-soft); color: var(--warn); }

  .bar { height: 8px; margin-top: 20px; border-radius: 99px; background: var(--surface-2); overflow: hidden; }
  .bar div { height: 100%; background: var(--accent-grad); border-radius: inherit; transition: width 0.3s ease; }
  .bar.indeterminate div { width: 35%; animation: slide 1.3s ease-in-out infinite; }
  @keyframes slide { from { transform: translateX(-100%); } to { transform: translateX(290%); } }
  .pct { font-size: 12px; margin-top: 6px; font-variant-numeric: tabular-nums; }

  .hint { margin-top: 18px; font-size: 13px; }
  .hint :global(svg) { color: var(--accent); flex: none; }

  .result { margin-top: 18px; padding: 12px 14px; border-radius: 10px; white-space: pre-wrap; font-size: 13.5px; }
  .result.done { background: var(--ok-soft); }
  .result.done.warn { background: var(--warn-soft); }
  .result.error { background: var(--bad-soft); }
  .result.cancelled { background: var(--warn-soft); }
  .note { margin-top: 8px; font-size: 13px; }

  details { margin-top: 18px; }
  summary { cursor: pointer; color: var(--text-2); font-size: 12.5px; font-weight: 550; }
  .log {
    margin-top: 8px; max-height: 220px; overflow: auto;
    padding: 12px 14px; border-radius: 10px;
    background: var(--bg); border: 1px solid var(--border);
    font-family: var(--mono); font-size: 12px; line-height: 1.6; white-space: pre-wrap;
  }

  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 22px; }
</style>
