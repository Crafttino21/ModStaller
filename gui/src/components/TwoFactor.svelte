<script lang="ts">
  import { ShieldCheck } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { ui } from "../lib/state.svelte";

  let code = $state("");
  const valid = $derived(/^\d{6}$/.test(code.trim()));

  function submit(e: Event) {
    e.preventDefault();
    if (valid) ui.twoFactor?.(code.trim());
  }
</script>

<Modal width={400} onclose={() => ui.twoFactor?.(null)}>
  <form onsubmit={submit}>
    <div class="icon"><ShieldCheck size={26} /></div>
    <h2>Bestätigungscode</h2>
    <p class="muted">Apple hat einen sechsstelligen Code an dein iPhone geschickt.</p>
    <!-- svelte-ignore a11y_autofocus -->
    <input type="text" inputmode="numeric" maxlength="6" autocomplete="one-time-code"
           placeholder="000000" bind:value={code} autofocus />
    <div class="actions">
      <button type="button" class="btn ghost" onclick={() => ui.twoFactor?.(null)}>Abbrechen</button>
      <button type="submit" class="btn primary" disabled={!valid}>Bestätigen</button>
    </div>
  </form>
</Modal>

<style>
  form { display: grid; gap: 10px; text-align: center; }
  .icon { width: 52px; height: 52px; margin: 0 auto 6px; border-radius: 15px; display: grid; place-items: center;
          background: var(--accent-soft); color: var(--accent); }
  input { margin-top: 10px; height: 54px; text-align: center; font-size: 26px; letter-spacing: 0.45em;
          font-variant-numeric: tabular-nums; font-weight: 600; }
  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }
</style>
