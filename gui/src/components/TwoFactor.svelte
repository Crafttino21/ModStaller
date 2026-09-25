<script lang="ts">
  import { ShieldCheck } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { ui } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";

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
    <h2>{t("Confirmation code")}</h2>
    <p class="muted">{t("Apple sent a six-digit code to your iPhone.")}</p>
    <!-- svelte-ignore a11y_autofocus -->
    <input type="text" inputmode="numeric" maxlength="6" autocomplete="one-time-code"
           placeholder="000000" bind:value={code} autofocus />
    <div class="actions">
      <button type="button" class="btn ghost" onclick={() => ui.twoFactor?.(null)}>{t("Cancel")}</button>
      <button type="submit" class="btn primary" disabled={!valid}>{t("Confirm")}</button>
    </div>
  </form>
</Modal>

<style>
  form { display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; text-align: center; }
  .icon { width: 52px; height: 52px; margin: 0 auto 6px; border-radius: 15px; display: grid; place-items: center;
          background: var(--accent-soft); color: var(--accent); }
  /* text-indent gleicht die Laufweite hinter der letzten Ziffer aus - sonst
     sitzt der Code sichtbar links aus der Mitte. */
  input { margin-top: 10px; height: 54px; text-align: center; font-size: 26px; letter-spacing: 0.45em;
          text-indent: 0.45em; font-variant-numeric: tabular-nums; font-weight: 600; }
  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }
</style>
