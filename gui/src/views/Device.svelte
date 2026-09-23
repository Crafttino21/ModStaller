<script lang="ts">
  import { Smartphone, TriangleAlert, Search, LoaderCircle, RefreshCw } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import DeviceChecks from "../components/DeviceChecks.svelte";
  import { errorText, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import type { DeviceApp, DeviceInfo } from "../lib/types";

  let info = $state<DeviceInfo | null>(null);
  let error = $state("");
  let apps = $state<DeviceApp[] | null>(null);
  let appsLoading = $state(false);
  let filter = $state("");

  const connected = $derived(!!ui.status?.device);

  async function load() {
    error = "";
    try {
      info = await call<DeviceInfo>("device.info");
    } catch (err) {
      info = null;
      error = errorText(err);
    }
  }

  async function loadApps() {
    appsLoading = true;
    try {
      apps = await call<DeviceApp[]>("device.apps");
    } catch (err) {
      error = errorText(err);
    } finally {
      appsLoading = false;
    }
  }

  // Beim An- und Abstecken neu laden.
  $effect(() => {
    if (connected) load();
    else { info = null; apps = null; }
  });

  const shown = $derived(
    (apps ?? []).filter((a) => !filter || `${a.name} ${a.bundleId}`.toLowerCase().includes(filter.toLowerCase())),
  );
</script>

<PageHeader title="Gerät" subtitle="Das angeschlossene iPhone." />

{#if ui.status?.deviceAttached}
  <div class="checks"><DeviceChecks /></div>
{/if}

{#if !connected}
  <div class="card empty">
    <Smartphone size={30} />
    <p>{ui.status?.deviceAttached ? "Angesteckt, aber nicht bereit – iPhone entsperren und „Vertrauen“ bestätigen." : "Kein iPhone verbunden. Per USB anstecken und entsperren."}</p>
    {#if ui.status?.error}<p class="faint small selectable">{ui.status.error}</p>{/if}
  </div>
{:else}
  {#if error}
    <div class="banner bad small"><TriangleAlert size={16} color="var(--bad)" /><div class="grow selectable">{error}</div></div>
  {/if}
  <div class="card pad">
    {#if !info}
      <div class="skeleton" style="height:120px"></div>
    {:else}
      <div class="head">
        <div class="phone"><Smartphone size={30} /></div>
        <div>
          <h2>{info.name}</h2>
          <p class="muted">{info.productType} · iOS {info.iosVersion} ({info.build})</p>
        </div>
      </div>
      <dl>
        <dt>UDID</dt><dd class="mono selectable">{info.udid}</dd>
        <dt>Entwicklermodus</dt>
        <dd>
          {#if info.developerMode}<span class="chip ok"><span class="dot"></span>an</span>
          {:else}<span class="chip bad"><span class="dot"></span>aus</span>
            <span class="muted small">Einstellungen › Datenschutz &amp; Sicherheit › Entwicklermodus – sonst startet keine sideloadete App.</span>{/if}
        </dd>
      </dl>
    {/if}
  </div>

  <div class="card pad">
    <div class="apps-head">
      <h2>Installierte Nutzer-Apps</h2>
      {#if apps}
        <div class="search"><Search size={15} /><input type="search" placeholder="Filtern" bind:value={filter} /></div>
        <button class="btn sm icon ghost" title="Neu laden" onclick={loadApps}><RefreshCw size={15} /></button>
      {/if}
    </div>
    {#if !apps}
      <button class="btn" onclick={loadApps} disabled={appsLoading}>
        {#if appsLoading}<LoaderCircle size={16} class="spin" />{/if} Apps auflisten
      </button>
    {:else}
      <p class="faint small">{apps.length} App(s)</p>
      <div class="apps">
        {#each shown as a (a.bundleId)}
          <div class="app"><span class="name">{a.name}</span><span class="faint mono tiny selectable">{a.bundleId}</span><span class="faint tiny">{a.version}</span></div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .checks { margin-bottom: 14px; }
  .pad { padding: 22px; margin-bottom: 14px; }
  .small { font-size: 13px; }
  .tiny { font-size: 11.5px; }
  .grow { flex: 1; min-width: 0; }
  .banner { margin-bottom: 14px; }
  .head { display: flex; gap: 16px; align-items: center; }
  .head p { margin-top: 3px; }
  .phone { width: 58px; height: 58px; border-radius: 16px; display: grid; place-items: center; background: var(--accent-grad); color: #fff; }
  dl { display: grid; grid-template-columns: 150px 1fr; gap: 12px 16px; margin: 22px 0 0; align-items: center; }
  dt { color: var(--text-2); font-size: 13px; }
  dd { margin: 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .apps-head { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .apps-head h2 { flex: 1; }
  .search { display: flex; align-items: center; gap: 6px; color: var(--text-3); }
  .search input { height: 32px; width: 200px; }
  .apps { display: grid; margin-top: 8px; max-height: 420px; overflow: auto; }
  .app { display: grid; grid-template-columns: minmax(160px, 1fr) 2fr auto; gap: 12px; padding: 8px 4px; align-items: center; }
  .app + .app { border-top: 1px solid var(--border); }
  .name { font-weight: 550; }
</style>
