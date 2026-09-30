<script lang="ts">
  import { Library, Plus, Trash2, LoaderCircle, TriangleAlert, X } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import StoreImage from "./StoreImage.svelte";
  import { errorText, toast } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { relative } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import type { StoreSource } from "../lib/types";

  let { onclose }: { onclose: () => void } = $props();

  let list = $state<StoreSource[] | null>(null);
  let url = $state("");
  let adding = $state(false);
  let error = $state("");

  call<StoreSource[]>("store.sources").then((l) => (list = l), (err) => (error = errorText(err)));

  async function add(e: Event) {
    e.preventDefault();
    if (!url.trim()) return;
    adding = true;
    error = "";
    try {
      const r = await call<{ name: string; apps: number }>("store.sources.add", { url: url.trim() });
      toast(t("Source added: {name} ({count} apps)", { name: r.name, count: r.apps }));
      url = "";
      list = await call<StoreSource[]>("store.sources");
    } catch (err) {
      error = errorText(err);
    } finally {
      adding = false;
    }
  }

  async function remove(s: StoreSource) {
    list = await call<StoreSource[]>("store.sources.remove", { url: s.url });
  }

  async function toggle(s: StoreSource, enabled: boolean) {
    list = await call<StoreSource[]>("store.sources.toggle", { url: s.url, enabled });
  }
</script>

<Modal width={560} {onclose}>
  <div class="head">
    <div class="icon"><Library size={22} /></div>
    <h2 class="grow">{t("Sources")}</h2>
    <button class="btn icon ghost" title={t("Close")} onclick={onclose}><X size={18} /></button>
  </div>
  <p class="muted small">
    {t("Sources in the AltStore format – the same ones AltStore and SideStore read. ModStaller comes with the official sources of AltStore, SideStore, UTM, PojavLauncher/Amethyst, iSH, StikDebug and several emulators.")}
  </p>

  <div class="list">
    {#if !list}
      <div class="faint row"><LoaderCircle size={16} class="spin" /></div>
    {:else}
      {#each list as s (s.url)}
        <div class="src">
          <StoreImage url={s.iconUrl} fallback={s.name || s.url} class="src-icon" />
          <div class="grow">
            <div class="name">{s.name || s.url}</div>
            <div class="faint tiny ell">{s.url}</div>
            <div class="faint tiny">
              {#if s.error}<span class="bad-text"><TriangleAlert size={12} /> {s.error}</span>
              {:else if s.fetchedAt}{t("{count} apps", { count: s.apps })} · {relative(s.fetchedAt)}{/if}
            </div>
            {#if s.notice === "jailbreak"}
              <div class="warn-text tiny"><TriangleAlert size={12} /> {t("Also lists jailbreak tools and exploits - they are marked and ask before installing.")}</div>
            {/if}
          </div>
          <label class="toggle-mini" title={t("Show in the store")}>
            <input type="checkbox" checked={s.enabled} onchange={(e) => toggle(s, e.currentTarget.checked)} />
          </label>
          <button class="btn sm icon ghost" title={t("Remove")} onclick={() => remove(s)}><Trash2 size={15} /></button>
        </div>
      {/each}
    {/if}
  </div>

  <form class="add" onsubmit={add}>
    <input type="url" placeholder="https://…/apps.json" bind:value={url} />
    <button class="btn primary" disabled={adding || !url.trim()}>
      {#if adding}<LoaderCircle size={15} class="spin" />{:else}<Plus size={15} />{/if} {t("Add")}
    </button>
  </form>
  {#if error}<p class="bad-text small selectable">{error}</p>{/if}
  <p class="faint tiny note">
    {t("Sources you add are your responsibility: ModStaller shows what they list, it does not check it. Only install apps you are allowed to use.")}
  </p>
</Modal>

<style>
  .head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .icon { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center;
          background: var(--accent-soft); color: var(--accent); }
  .grow { flex: 1; min-width: 0; }
  .list { display: grid; gap: 6px; margin: 14px 0; }
  .src { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 11px;
         border: 1px solid var(--border); }
  .src :global(.src-icon) { width: 36px; height: 36px; border-radius: 9px; }
  .name { font-weight: 550; }
  .ell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .add { display: flex; gap: 8px; }
  .add input { flex: 1; height: 36px; }
  .row { display: flex; gap: 8px; padding: 10px; }
  .small { font-size: 13px; }
  .tiny { font-size: 11.5px; }
  .note { margin-top: 12px; }
  .bad-text { color: var(--bad); display: inline-flex; align-items: center; gap: 4px; }
  .warn-text { color: var(--warn); display: flex; align-items: center; gap: 4px; margin-top: 2px; }
  .toggle-mini input { width: 16px; height: 16px; cursor: pointer; }
</style>
