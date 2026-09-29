<script lang="ts">
  import { Tv, LoaderCircle, RefreshCw } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { busy, errorText, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { pairTv } from "../lib/actions";
  import { t } from "../lib/i18n.svelte";
  import type { PairableTv } from "../lib/types";

  // Das Apple TV wirbt nur, solange sein Koppel-Bildschirm offen ist - also
  // suchen, bis eins auftaucht, und dann die Liste zeigen.
  let found = $state<PairableTv[] | null>(null);
  let searching = $state(false);
  let error = $state("");

  async function search() {
    searching = true;
    error = "";
    try {
      found = await call<PairableTv[]>("pair.browse");
    } catch (err) {
      error = errorText(err);
      found = [];
    } finally {
      searching = false;
    }
  }

  search();

  function close() {
    ui.pairingOpen = false;
  }

  function pick(tv: PairableTv) {
    close();
    pairTv(tv);
  }
</script>

<Modal width={480} onclose={close}>
  <div class="icon"><Tv size={26} /></div>
  <h2>{t("Pair Apple TV")}</h2>
  <ol class="muted steps">
    <li>{t("On the Apple TV open Settings › Remotes and Devices › Remote App and Devices.")}</li>
    <li>{t("Keep that screen open and pick the Apple TV below.")}</li>
    <li>{t("Type in the PIN the Apple TV then shows.")}</li>
  </ol>

  <div class="list">
    {#if searching && !found?.length}
      <div class="faint row"><LoaderCircle size={16} class="spin" /> {t("Looking in the network …")}</div>
    {:else if found?.length}
      {#each found as tv (tv.identifier)}
        <button class="tv" disabled={busy()} onclick={() => pick(tv)}>
          <Tv size={18} />
          <span class="name">{tv.name}</span>
          <span class="faint mono tiny">{tv.host}</span>
        </button>
      {/each}
    {:else}
      <div class="faint row">{t("No Apple TV found. Is the pairing screen open and the Apple TV in the same network?")}</div>
    {/if}
    {#if error}<p class="small bad-text selectable">{error}</p>{/if}
  </div>

  <div class="actions">
    <button class="btn ghost" onclick={close}>{t("Cancel")}</button>
    <button class="btn" disabled={searching} onclick={search}>
      {#if searching}<LoaderCircle size={15} class="spin" />{:else}<RefreshCw size={15} />{/if} {t("Search again")}
    </button>
  </div>
</Modal>

<style>
  .icon { width: 52px; height: 52px; margin-bottom: 12px; border-radius: 15px; display: grid; place-items: center;
          background: var(--accent-soft); color: var(--accent); }
  .steps { margin: 10px 0 16px; padding-left: 20px; display: grid; gap: 4px; font-size: 13.5px; }
  .list { display: grid; gap: 6px; min-height: 48px; }
  .row { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 10px 2px; }
  .tv { display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 11px;
        border: 1px solid var(--border-strong); background: var(--surface-2); color: var(--text);
        font: inherit; cursor: pointer; text-align: left; }
  .tv:hover { border-color: var(--accent); }
  .name { flex: 1; font-weight: 550; }
  .tiny { font-size: 11.5px; }
  .small { font-size: 13px; }
  .bad-text { color: var(--bad); }
  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
</style>
