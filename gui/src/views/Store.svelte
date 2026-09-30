<script lang="ts">
  import {
    Search, RefreshCw, Library, LoaderCircle, ArrowUpCircle, Store as StoreIconLucide, TriangleAlert,
  } from "@lucide/svelte";
  import { warningLabel } from "../lib/store";
  import PageHeader from "../components/PageHeader.svelte";
  import StoreImage from "../components/StoreImage.svelte";
  import StoreAppDialog from "../components/StoreAppDialog.svelte";
  import StoreSources from "../components/StoreSources.svelte";
  import { busy, errorText, refreshStoreUpdates, storeUpdateFor, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { mb } from "../lib/format";
  import { storeUpdate } from "../lib/actions";
  import { t } from "../lib/i18n.svelte";
  import type { StoreApp, StoreList, StoreSource } from "../lib/types";

  const PAGE = 60;

  let query = $state("");
  let source = $state("");
  let category = $state("");
  let items = $state<StoreApp[]>([]);
  let total = $state(0);
  let categories = $state<string[]>([]);
  let sources = $state<StoreSource[]>([]);
  let loading = $state(false);
  let error = $state("");
  let selected = $state<StoreApp | null>(null);
  let managing = $state(false);
  let sentinel = $state<HTMLElement | null>(null);

  const sourceName = (url: string) => sources.find((s) => s.url === url)?.name || url.replace(/^https:\/\//, "");
  /** Installiert ist, was ModStaller unter der Original-Bundle-ID kennt. */
  const installed = (app: StoreApp) => ui.status?.apps.some((a) => a.originalBundleId === app.bundleId) ?? false;
  const activeSources = $derived(sources.filter((s) => s.enabled && s.apps));

  let seq = 0;
  async function load(reset: boolean) {
    const mine = ++seq;
    loading = true;
    error = "";
    try {
      const r = await call<StoreList>("store.list", {
        query, source: source || undefined, category: category || undefined,
        offset: reset ? 0 : items.length, limit: PAGE,
      });
      if (mine !== seq) return;
      items = reset ? r.items : [...items, ...r.items];
      total = r.total;
      categories = r.categories;
    } catch (err) {
      if (mine === seq) error = errorText(err);
    } finally {
      if (mine === seq) loading = false;
    }
  }

  async function loadSources() {
    try {
      sources = await call<StoreSource[]>("store.sources");
    } catch {
      sources = [];
    }
  }

  async function reloadAll() {
    loading = true;
    try {
      sources = await call<StoreSource[]>("store.refresh");
    } catch (err) {
      error = errorText(err);
    }
    await load(true);
    refreshStoreUpdates(true);
  }

  // Suche leicht verzoegert - nicht bei jedem Tastendruck.
  let timer: ReturnType<typeof setTimeout> | undefined;
  $effect(() => {
    void query; void source; void category;
    clearTimeout(timer);
    timer = setTimeout(() => load(true), 250);
    return () => clearTimeout(timer);
  });

  loadSources();
  refreshStoreUpdates();

  // Nachladen, wenn das Ende der Liste ins Bild kommt.
  $effect(() => {
    if (!sentinel) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting) && !loading && items.length < total) load(false);
    }, { rootMargin: "400px" });
    io.observe(sentinel);
    return () => io.disconnect();
  });

  function closeSources() {
    managing = false;
    loadSources();
    load(true);
  }
</script>

<PageHeader title={t("Store")} subtitle={t("Apps from AltStore-compatible sources – signed with your Apple account and installed like any IPA.")} />

{#if ui.storeUpdates.length}
  <div class="card updates">
    <h2><ArrowUpCircle size={18} /> {t("Updates available")}</h2>
    {#each ui.storeUpdates as u (u.bundleId)}
      <div class="upd">
        <div class="grow">
          <div class="name">{u.name}</div>
          <div class="faint small">{u.installed || "?"} → {u.offered} · {sourceName(u.source)}</div>
        </div>
        <button class="btn sm primary" disabled={busy() || !ui.status?.device} onclick={() => storeUpdate(u)}>
          {t("Update")}
        </button>
      </div>
    {/each}
  </div>
{/if}

<div class="toolbar">
  <div class="search"><Search size={16} />
    <input type="search" placeholder={t("Search apps")} bind:value={query} />
  </div>
  <button class="btn sm" onclick={() => (managing = true)}><Library size={15} /> {t("Sources")}</button>
  <button class="btn sm icon ghost" title={t("Reload sources")} disabled={loading} onclick={reloadAll}>
    <RefreshCw size={15} />
  </button>
</div>

{#if activeSources.length > 1 || categories.length}
  <div class="chips">
    {#if activeSources.length > 1}
      <button class="chip-btn" class:on={!source} onclick={() => (source = "")}>{t("All sources")}</button>
      {#each activeSources as s (s.url)}
        <button class="chip-btn" class:on={source === s.url} onclick={() => (source = s.url)}>{s.name || s.url}</button>
      {/each}
    {/if}
    {#if categories.length}
      <span class="sep"></span>
      <button class="chip-btn" class:on={!category} onclick={() => (category = "")}>{t("All")}</button>
      {#each categories as c (c)}
        <button class="chip-btn" class:on={category === c} onclick={() => (category = c)}>{c}</button>
      {/each}
    {/if}
  </div>
{/if}

{#if error}
  <div class="banner bad small">{error}</div>
{/if}

{#if !items.length && loading}
  <div class="card empty"><LoaderCircle size={28} class="spin" /><p>{t("Loading sources …")}</p></div>
{:else if !items.length}
  <div class="card empty">
    <StoreIconLucide size={30} />
    <p>{query ? t("No app matches “{query}”.", { query }) : t("No apps - add a source under “Sources”.")}</p>
  </div>
{:else}
  <p class="faint small count">{t("{count} apps", { count: total })}</p>
  <div class="grid">
    {#each items as app (app.source + app.bundleId)}
      {@const upd = ui.storeUpdates.find((u) => u.storeBundleId === app.bundleId && u.source === app.source)}
      <button class="card app" onclick={() => (selected = app)}>
        <StoreImage url={app.iconUrl} fallback={app.name} alt="" class="icon" />
        <div class="info">
          <div class="name">{app.name}</div>
          <div class="faint small ell">{app.developer || sourceName(app.source)}</div>
          <div class="meta">
            <span class="ver" title={app.version}>{app.version}</span>
            {#if app.size}<span>· {mb(app.size)}</span>{/if}
            {#if upd}<span class="chip warn">{t("Update")}</span>
            {:else if installed(app)}<span class="chip ok">{t("Installed")}</span>{/if}
            {#if (app.offers ?? 1) > 1}<span class="chip">{t("{count} sources", { count: app.offers ?? 1 })}</span>{/if}
            {#if app.warning}<span class="chip bad"><TriangleAlert size={11} /> {warningLabel(app.warning)}</span>{/if}
          </div>
        </div>
      </button>
    {/each}
  </div>
  <div bind:this={sentinel} class="sentinel">
    {#if loading}<LoaderCircle size={18} class="spin" />{/if}
  </div>
{/if}

{#if selected}
  <StoreAppDialog app={selected} {sourceName}
                  update={storeUpdateFor(ui.status?.apps.find((a) => a.originalBundleId === selected?.bundleId)?.bundleId ?? "")}
                  installed={installed(selected)} onclose={() => (selected = null)} />
{/if}
{#if managing}
  <StoreSources onclose={closeSources} />
{/if}

<style>
  .updates { padding: 18px 20px; margin-bottom: 16px; display: grid; gap: 10px; }
  .updates h2 { display: flex; align-items: center; gap: 8px; font-size: 16px; }
  .upd { display: flex; align-items: center; gap: 12px; padding-top: 10px; border-top: 1px solid var(--border); }
  .toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
  .search { flex: 1; display: flex; align-items: center; gap: 8px; color: var(--text-3); }
  .search input { flex: 1; height: 36px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; align-items: center; }
  .chip-btn { padding: 5px 11px; border-radius: 99px; border: 1px solid var(--border-strong); background: transparent;
              color: var(--text-2); font: inherit; font-size: 12.5px; cursor: pointer; text-transform: capitalize; }
  .chip-btn.on { background: var(--accent-soft); border-color: var(--accent); color: var(--text); }
  .sep { width: 1px; height: 18px; background: var(--border); margin: 0 4px; }
  .count { margin-bottom: 8px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
  .app { display: flex; gap: 12px; align-items: center; padding: 12px; text-align: left; cursor: pointer;
         font: inherit; color: inherit; transition: border-color 0.15s; min-width: 0; }
  .app:hover { border-color: var(--border-strong); }
  .app :global(.icon) { width: 56px; height: 56px; border-radius: 13px; }
  .info { min-width: 0; flex: 1; display: grid; gap: 2px; }
  .name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .meta { display: flex; gap: 6px; align-items: center; font-size: 12px; color: var(--text-3); flex-wrap: wrap;
          min-width: 0; }
  /* Manche Quellen haben Build-Kennungen als Version ("0.1.gha.4865233241..."). */
  .ver { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .small { font-size: 12.5px; }
  .grow { flex: 1; min-width: 0; }
  .sentinel { display: grid; place-items: center; min-height: 40px; color: var(--accent); }
  .banner { margin-bottom: 12px; }
</style>
