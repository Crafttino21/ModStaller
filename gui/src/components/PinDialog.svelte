<script lang="ts">
  import { Tv } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { ui } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";

  // Die PIN, die das Apple TV beim Koppeln auf dem Bildschirm zeigt.
  let pin = $state("");
  const valid = $derived(/^\d{4,8}$/.test(pin.trim()));

  function submit(e: Event) {
    e.preventDefault();
    if (valid) ui.pin?.(pin.trim());
  }
</script>

<Modal width={400} onclose={() => ui.pin?.(null)}>
  <form onsubmit={submit}>
    <div class="icon"><Tv size={26} /></div>
    <h2>{t("PIN from the Apple TV")}</h2>
    <p class="muted">{t("The Apple TV now shows a code on the screen. Type it in here.")}</p>
    {#if ui.pinFor}<p class="faint who selectable">{ui.pinFor}</p>{/if}
    <!-- svelte-ignore a11y_autofocus -->
    <input type="text" inputmode="numeric" maxlength="8" autocomplete="off"
           placeholder="0000" bind:value={pin} autofocus />
    <div class="actions">
      <button type="button" class="btn ghost" onclick={() => ui.pin?.(null)}>{t("Cancel")}</button>
      <button type="submit" class="btn primary" disabled={!valid}>{t("Pair")}</button>
    </div>
  </form>
</Modal>

<style>
  form { display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; text-align: center; }
  .icon { width: 52px; height: 52px; margin: 0 auto 6px; border-radius: 15px; display: grid; place-items: center;
          background: var(--accent-soft); color: var(--accent); }
  input { margin-top: 10px; height: 54px; text-align: center; font-size: 26px; letter-spacing: 0.45em;
          text-indent: 0.45em; font-variant-numeric: tabular-nums; font-weight: 600; }
  .who { font-size: 13px; font-weight: 550; }
  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }
</style>
