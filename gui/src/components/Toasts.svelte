<script lang="ts">
  import { CircleCheck, CircleX, TriangleAlert } from "@lucide/svelte";
  import { fly } from "svelte/transition";
  import { flip } from "svelte/animate";
  import { dismiss, ui } from "../lib/state.svelte";
</script>

<div class="stack">
  {#each ui.toasts as t (t.id)}
    <button class="toast card {t.tone}" onclick={() => dismiss(t.id)}
            in:fly={{ y: 16, duration: 180 }} out:fly={{ x: 40, duration: 160 }} animate:flip={{ duration: 180 }}>
      {#if t.tone === "ok"}<CircleCheck size={18} />{:else if t.tone === "warn"}<TriangleAlert size={18} />{:else}<CircleX size={18} />{/if}
      <span>{t.text}</span>
    </button>
  {/each}
</div>

<style>
  .stack { position: fixed; right: 20px; bottom: 20px; z-index: 60; display: grid; gap: 8px; width: 360px; }
  .toast {
    display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px;
    font: inherit; font-size: 13px; color: var(--text); text-align: left; cursor: pointer;
    white-space: pre-line;
  }
  .toast :global(svg) { flex: none; margin-top: 1px; }
  .ok :global(svg) { color: var(--ok); }
  .warn :global(svg) { color: var(--warn); }
  .bad :global(svg) { color: var(--bad); }
</style>
