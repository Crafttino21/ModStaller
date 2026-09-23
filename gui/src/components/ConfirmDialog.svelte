<script lang="ts">
  import { TriangleAlert } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { ui } from "../lib/state.svelte";

  const c = $derived(ui.confirm!);
  let option = $state(false);
</script>

<Modal width={440} onclose={() => c.resolve({ ok: false, option })}>
  <div class="body">
    {#if c.danger}<div class="icon"><TriangleAlert size={22} /></div>{/if}
    <div>
      <h2>{c.title}</h2>
      <p class="muted">{c.text}</p>
      {#if c.option}
        <label class="opt"><input type="checkbox" bind:checked={option} /> {c.option}</label>
      {/if}
    </div>
  </div>
  <div class="actions">
    <button class="btn ghost" onclick={() => c.resolve({ ok: false, option })}>Abbrechen</button>
    <button class="btn {c.danger ? 'danger solid' : 'primary'}" onclick={() => c.resolve({ ok: true, option })}>
      {c.confirm}
    </button>
  </div>
</Modal>

<style>
  .body { display: flex; gap: 14px; }
  .body p { margin-top: 6px; white-space: pre-line; }
  .icon { width: 42px; height: 42px; flex: none; border-radius: 12px; display: grid; place-items: center;
          background: var(--bad-soft); color: var(--bad); }
  .opt { display: flex; gap: 8px; align-items: center; margin-top: 14px; font-size: 13px; cursor: pointer; }
  .opt input { accent-color: var(--accent); width: 16px; height: 16px; }
  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 22px; }
</style>
