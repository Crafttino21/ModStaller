<script lang="ts">
  import { Zap, RefreshCw, Trash2, Download, TriangleAlert } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import ExpiryRing from "../components/ExpiryRing.svelte";
  import { busy, go, ui } from "../lib/state.svelte";
  import { date, days } from "../lib/format";
  import { enableJit, refreshApps, uninstallApp } from "../lib/actions";

  const st = $derived(ui.status);
  const noDevice = $derived(!st?.device);
</script>

<PageHeader title="Apps" subtitle="Was ModStaller installiert hat. Kostenlose Konten: höchstens 3 Apps, je 7 Tage gültig.">
  {#snippet actions()}
    <button class="btn" disabled={busy() || noDevice || !st?.urgent.length} onclick={() => refreshApps()}
            title={st?.urgent.length ? "" : "Gerade ist nichts fällig"}>
      <RefreshCw size={16} /> Fällige erneuern
    </button>
    <button class="btn primary" onclick={() => go("install")}><Download size={16} /> Installieren</button>
  {/snippet}
</PageHeader>

{#if noDevice && st?.apps.length}
  <div class="banner info note">
    <div class="grow">Zum Erneuern, Freischalten oder Entfernen muss das iPhone angesteckt und entsperrt sein.</div>
  </div>
{/if}

{#if !st?.apps.length}
  <div class="card empty">
    <Download size={30} />
    <p>Noch nichts über ModStaller installiert.</p>
    <button class="btn primary" onclick={() => go("install")}>App installieren</button>
  </div>
{:else}
  <div class="card list">
    {#each st.apps as app (app.bundleId)}
      <div class="row">
        <ExpiryRing daysLeft={app.daysLeft} urgentDays={st.urgentDays} size={48} />
        <div class="grow">
          <div class="name">{app.name}</div>
          <div class="faint mono small selectable">{app.bundleId}</div>
          <div class="small" class:warn={app.urgent}>{days(app.daysLeft)} · bis {date(app.expiresAt)}</div>
          {#if app.sourceMissing}
            <div class="small missing"><TriangleAlert size={13} /> Original-IPA fehlt ({app.sourceIpa}) – Erneuern nicht möglich.</div>
          {/if}
        </div>
        <div class="acts">
          <button class="btn sm" disabled={busy() || noDevice} onclick={() => enableJit(app)}>
            <Zap size={15} /> JIT
          </button>
          <button class="btn sm" disabled={busy() || noDevice || app.sourceMissing} onclick={() => refreshApps(app)}>
            <RefreshCw size={15} /> Erneuern
          </button>
          <button class="btn sm icon danger" title="Vom iPhone entfernen" disabled={busy() || noDevice}
                  onclick={() => uninstallApp(app)}>
            <Trash2 size={15} />
          </button>
        </div>
      </div>
    {/each}
  </div>

  <p class="faint foot">
    <b>JIT</b> brauchen Java- und Emulator-Apps (z.&nbsp;B. Minecraft-Launcher): ModStaller startet die App mit
    angehängtem Debugger und gibt Speicher frei, sobald sie danach fragt.
  </p>
{/if}

<style>
  .note { margin-bottom: 14px; font-size: 13px; }
  .list { padding: 6px; }
  .row { display: flex; gap: 16px; align-items: center; padding: 14px 12px; border-radius: 10px; }
  .row + .row { border-top: 1px solid var(--border); border-radius: 0; }
  .grow { flex: 1; min-width: 0; display: grid; gap: 1px; }
  .name { font-weight: 650; font-size: 15px; }
  .small { font-size: 12.5px; color: var(--text-2); }
  .mono.small { font-size: 11.5px; color: var(--text-3); }
  .warn { color: var(--warn); }
  .missing { display: flex; gap: 5px; align-items: center; color: var(--bad); }
  .acts { display: flex; gap: 6px; }
  .foot { margin-top: 16px; font-size: 12.5px; max-width: 720px; }
  .foot b { color: var(--text-2); }
</style>
