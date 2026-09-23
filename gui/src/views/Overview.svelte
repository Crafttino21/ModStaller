<script lang="ts">
  import {
    Smartphone, UserRound, TriangleAlert, RefreshCw, Zap, Download, ChevronRight, Lock,
  } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import ExpiryRing from "../components/ExpiryRing.svelte";
  import DeviceChecks from "../components/DeviceChecks.svelte";
  import PhoneMockup from "../components/PhoneMockup.svelte";
  import BatteryLevel from "../components/BatteryLevel.svelte";
  import { busy, go, ui } from "../lib/state.svelte";
  import { date, days } from "../lib/format";
  import { enableJit, refreshApps } from "../lib/actions";

  const st = $derived(ui.status);
  const urgent = $derived(st?.apps.filter((a) => a.urgent) ?? []);
</script>

<PageHeader title="Übersicht" subtitle="iPhone, Anmeldung und was demnächst abläuft – auf einen Blick." />

{#if urgent.length}
  <div class="banner warn urgent">
    <TriangleAlert size={20} color="var(--warn)" />
    <div class="grow">
      <strong>{urgent[0].name}</strong>
      {urgent[0].daysLeft < 0 ? "ist abgelaufen" : `läuft ab – ${days(urgent[0].daysLeft)}`}
      {#if urgent.length > 1}<span class="muted"> und {urgent.length - 1} weitere</span>{/if}
    </div>
    <button class="btn sm primary" disabled={busy() || !st?.device} onclick={() => refreshApps()}>
      <RefreshCw size={15} /> Jetzt erneuern
    </button>
  </div>
{/if}

<div class="tiles">
  <div class="card tile">
    {#if st?.device}
      <div class="mock"><PhoneMockup form={st.device.formFactor} height={62} /></div>
    {:else}
      <div class="tile-icon"><Smartphone size={22} /></div>
    {/if}
    <div class="grow">
      <div class="label">{st?.device?.formFactor === "ipad" ? "iPad" : "iPhone"}</div>
      {#if st?.device}
        <div class="value">{st.device.name}</div>
        <div class="model">{st.device.model}</div>
        <div class="chips">
          <span class="chip">iOS {st.device.iosVersion}</span>
          {#if st.device.battery}
            <span class="chip"><BatteryLevel level={st.device.battery.level} charging={st.device.battery.charging} /></span>
          {/if}
          {#if st.device.developerMode}
            <span class="chip ok"><span class="dot"></span>Entwicklermodus an</span>
          {:else}
            <span class="chip warn"><span class="dot"></span>Entwicklermodus aus</span>
          {/if}
        </div>
      {:else if st?.deviceAttached}
        <div class="value">Angesteckt, aber nicht bereit</div>
        <div class="hint"><Lock size={13} /> {st.error || "iPhone entsperren und „Vertrauen“ bestätigen."}</div>
      {:else}
        <div class="value dim">Nicht verbunden</div>
        <div class="hint">Per USB anstecken und entsperren.</div>
      {/if}
    </div>
  </div>

  <button class="card tile link" onclick={() => go("account")}>
    <div class="tile-icon" class:on={st?.loggedIn}><UserRound size={22} /></div>
    <div class="grow">
      <div class="label">Apple-Konto</div>
      {#if st?.loggedIn}
        <div class="value">Angemeldet</div>
        <div class="hint">Kontingente und Zertifikate ansehen</div>
      {:else}
        <div class="value dim">Nicht angemeldet</div>
        <div class="hint">Einmal anmelden, dann signiert ModStaller selbst.</div>
      {/if}
    </div>
    <ChevronRight size={18} class="chev" />
  </button>
</div>

{#if st?.deviceAttached}
  <div class="checks"><DeviceChecks compact /></div>
{/if}

<div class="section-head">
  <h2>Deine Apps</h2>
  {#if st?.apps.length}
    <button class="btn sm ghost" onclick={() => go("apps")}>Alle verwalten <ChevronRight size={15} /></button>
  {/if}
</div>

{#if !st}
  <div class="grid">
    {#each [1, 2] as _}<div class="card app"><div class="skeleton" style="height:54px"></div></div>{/each}
  </div>
{:else if !st.apps.length}
  <div class="card empty">
    <Download size={30} />
    <div>
      <h3 style="color: var(--text)">Noch keine App installiert</h3>
      <p>Zieh eine IPA ins Fenster oder wähle eine aus deinen Downloads.</p>
    </div>
    <button class="btn primary" onclick={() => go("install")}>App installieren</button>
  </div>
{:else}
  <div class="grid">
    {#each st.apps as app (app.bundleId)}
      <div class="card app">
        <ExpiryRing daysLeft={app.daysLeft} urgentDays={st.urgentDays} />
        <div class="grow info">
          <div class="app-name">{app.name}</div>
          <div class="faint mono small">{app.bundleId}</div>
          <div class="small" class:warn={app.urgent}>
            {days(app.daysLeft)} · bis {date(app.expiresAt)}
          </div>
        </div>
        <div class="app-actions">
          <button class="btn sm icon" title="JIT freischalten" disabled={busy() || !st.device}
                  onclick={() => enableJit(app)}><Zap size={16} /></button>
          <button class="btn sm icon" title="Jetzt erneuern" disabled={busy() || !st.device || app.sourceMissing}
                  onclick={() => refreshApps(app)}><RefreshCw size={16} /></button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .urgent { margin-bottom: 18px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
  .tile { display: flex; gap: 16px; align-items: center; padding: 20px; font: inherit; color: inherit; text-align: left; }
  .tile.link { cursor: pointer; transition: border-color 0.15s; }
  .tile.link:hover { border-color: var(--border-strong); }
  .tile :global(.chev) { color: var(--text-3); }
  .tile-icon { width: 48px; height: 48px; flex: none; border-radius: 14px; display: grid; place-items: center;
               background: var(--surface-2); color: var(--text-3); }
  .tile-icon.on { background: var(--accent-grad); color: #fff; box-shadow: 0 6px 18px rgb(110 100 255 / 0.3); }
  .label { font-size: 12px; font-weight: 600; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.05em; }
  .value { font-size: 17px; font-weight: 650; margin-top: 2px; }
  .model { font-size: 13px; color: var(--text-2); }
  .mock { width: 48px; display: grid; place-items: center; flex: none; }
  .value.dim { color: var(--text-2); }
  .chips { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
  .hint { display: flex; align-items: center; gap: 5px; font-size: 13px; color: var(--text-2); margin-top: 4px; }
  .grow { flex: 1; min-width: 0; }

  .checks { margin-top: 14px; }
  .section-head { display: flex; align-items: center; justify-content: space-between; margin: 30px 0 12px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 12px; }
  .app { display: flex; gap: 14px; align-items: center; padding: 16px; }
  .info { display: grid; gap: 1px; }
  .app-name { font-weight: 650; font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .small { font-size: 12.5px; color: var(--text-2); }
  .mono.small { font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .warn { color: var(--warn); }
  .app-actions { display: flex; gap: 6px; }
</style>
