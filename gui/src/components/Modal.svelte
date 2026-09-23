<script lang="ts">
  import type { Snippet } from "svelte";
  import { fade, scale } from "svelte/transition";

  let { onclose, width = 460, children }:
    { onclose?: () => void; width?: number; children: Snippet } = $props();

  function key(e: KeyboardEvent) {
    if (e.key === "Escape" && onclose) onclose();
  }
</script>

<svelte:window onkeydown={key} />

<div class="backdrop" transition:fade={{ duration: 140 }}>
  <div class="modal card" style:width="{width}px" role="dialog" aria-modal="true"
       transition:scale={{ duration: 160, start: 0.96 }}>
    {@render children()}
  </div>
</div>

<style>
  .backdrop {
    position: fixed; inset: 0; z-index: 50;
    display: grid; place-items: center; padding: 24px;
    background: rgb(5 6 10 / 0.55);
    backdrop-filter: blur(6px);
  }
  .modal { max-width: 100%; max-height: calc(100vh - 48px); overflow: auto; padding: 24px; }
</style>
