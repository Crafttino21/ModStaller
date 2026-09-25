<script lang="ts">
  import { Zap, RefreshCw, Trash2, Download, TriangleAlert, Package, LoaderCircle } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import ExpiryRing from "../components/ExpiryRing.svelte";
  import { busy, errorText, go, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { basename, date, days } from "../lib/format";
  import { enableJit, refreshApps, uninstallApp } from "../lib/actions";
  import { t } from "../lib/i18n.svelte";
  import type { SideloadedApp } from "../lib/types";

  const st = $derived(ui.status);
  const noDevice = $derived(!st?.device);

  // -- Fremde Sideloads ------------------------------------------------------
  //
  // Die eigenen Apps kommen aus dem Status und aktualisieren sich von selbst.
  // Was andere Werkzeuge abgelegt haben, steht nur auf dem iPhone - das kostet
  // eine eigene Abfrage und wird deshalb nur je Geraet einmal geholt.

  let foreign = $state<SideloadedApp[] | null>(null);
  let loading = $state(false);
  let error = $state("");
  let loadedFor: string | null = null;

  async function load() {
    if (!st?.deviceAttached) return;
    loading = true;
    error = "";
    try {
      const all = await call<SideloadedApp[]>("apps.overview");
      foreign = all.filter((a) => !a.managed);
    } catch (err) {
      error = errorText(err);
      foreign = null;
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    const key = st?.device?.udid ?? null;
    if (!key) {
      loadedFor = null;
      foreign = null;
      return;
    }
    if (key !== loadedFor && !loading) {
      loadedFor = key;
      load();
    }
  });

  const originText = $derived<Record<string, string>>({
    developer: t("Developer-signed"),
    other: t("Signed by someone else"),
    testflight: "TestFlight",
    store: "App Store",
  });
</script>

<PageHeader title={t("Apps")} subtitle={t("What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.")}>
  {#snippet actions()}
    <button class="btn" disabled={busy() || noDevice || !st?.urgent.length} onclick={() => refreshApps()}
            title={st?.urgent.length ? "" : t("Nothing is due right now")}>
      <RefreshCw size={16} /> {t("Renew due")}
    </button>
    <button class="btn primary" onclick={() => go("install")}><Download size={16} /> {t("Install")}</button>
  {/snippet}
</PageHeader>

{#if noDevice && st?.apps.length}
  <div class="banner info note">
    <div class="grow">{t("To renew, unlock or remove, the iPhone has to be connected and unlocked.")}</div>
  </div>
{/if}

{#if !st?.apps.length}
  <div class="card empty">
    <Download size={30} />
    <p>{t("Nothing installed through ModStaller yet.")}</p>
    <button class="btn primary" onclick={() => go("install")}>{t("Install app")}</button>
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
            <div class="small missing"><TriangleAlert size={13} /> {t("Source missing ({path}) – renewing is not possible.", { path: app.sourceIpa })}</div>
          {:else}
            <div class="small source selectable" title={app.sourceIpa}>
              <Package size={13} /> {basename(app.sourceIpa)}
            </div>
          {/if}
        </div>
        <div class="acts">
          <button class="btn sm" disabled={busy() || noDevice} onclick={() => enableJit(app)}>
            <Zap size={15} /> JIT
          </button>
          <button class="btn sm" disabled={busy() || noDevice || app.sourceMissing} onclick={() => refreshApps(app)}>
            <RefreshCw size={15} /> {t("Renew")}
          </button>
          <button class="btn sm icon danger" title={t("Remove from the iPhone")} disabled={busy() || noDevice}
                  onclick={() => uninstallApp(app)}>
            <Trash2 size={15} />
          </button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<!-- Was andere Werkzeuge abgelegt haben ------------------------------------ -->

{#if !noDevice}
  <div class="section">
    <div class="sec-head">
      <h2>{t("From other tools")}</h2>
      <button class="btn sm" onclick={load} disabled={loading}>
        {#if loading}<LoaderCircle size={14} class="spin" />{:else}<RefreshCw size={14} />{/if} {t("Read again")}
      </button>
    </div>
    <p class="muted sub">
      {t("Sideloads on the iPhone that do not come from ModStaller – from AltStore or SideStore, for instance. Renewing is not possible: the original IPA and the private key live with the other tool.")}
    </p>

    {#if error}
      <div class="banner bad small"><TriangleAlert size={16} color="var(--bad)" />
        <div class="grow selectable">{error}</div></div>
    {:else if foreign === null}
      <div class="card pad"><div class="skeleton" style="height:48px"></div></div>
    {:else if !foreign.length}
      <div class="card pad"><p class="faint">{t("Nothing found – everything on the iPhone comes from the store or from ModStaller.")}</p></div>
    {:else}
      <div class="card list">
        {#each foreign as app (app.bundleId)}
          <div class="row">
            <div class="badge"><Package size={20} /></div>
            <div class="grow">
              <div class="name">{app.name}{#if app.version}<span class="faint ver">{app.version}</span>{/if}</div>
              <div class="faint mono small selectable">{app.bundleId}</div>
              <div class="small faint selectable" title={app.signer}>
                {(originText[app.origin] ?? app.origin) + (app.teamId ? ` · Team ${app.teamId}` : "")}
              </div>
            </div>
            <div class="acts">
              {#if app.developerSigned}
                <button class="btn sm" disabled={busy()} onclick={() => enableJit(app)}><Zap size={15} /> JIT</button>
              {/if}
              <button class="btn sm icon danger" title={t("Remove from the iPhone")} disabled={busy()}
                      onclick={() => uninstallApp(app, true)}>
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

{#if st?.apps.length}
  <p class="faint foot">
    {@html t("<b>JIT</b> is needed by Java and emulator apps (Minecraft launchers, for example): ModStaller starts the app with a debugger attached and releases memory as soon as it asks for it.")}
  </p>
{/if}

<style>
  .note { margin-bottom: 14px; font-size: 13px; }
  .list { padding: 6px; }
  .row { display: flex; gap: 16px; align-items: center; padding: 14px 12px; border-radius: 10px; }
  .row + .row { border-top: 1px solid var(--border); border-radius: 0; }
  .grow { flex: 1; min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr); gap: 1px; }
  .name { font-weight: 650; font-size: 15px; }
  .ver { margin-left: 7px; font-weight: 400; font-size: 13px; }
  .small { font-size: 12.5px; color: var(--text-2); }
  .mono.small { font-size: 11.5px; color: var(--text-3); }
  /* Lange Bundle-IDs und Pfade duerfen die Zeile nicht sprengen. */
  .grow > div { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .warn { color: var(--warn); }
  .missing, .source { display: flex; gap: 5px; align-items: center; }
  .missing { color: var(--bad); }
  .acts { display: flex; gap: 6px; flex: none; }
  .badge { width: 48px; height: 48px; flex: none; border-radius: 12px; display: grid; place-items: center;
           background: var(--surface-2); color: var(--text-3); }
  .section { margin-top: 26px; }
  .sec-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .sub { margin: 6px 0 12px; font-size: 13px; max-width: 760px; }
  .pad { padding: 18px; }
  .foot { margin-top: 20px; font-size: 12.5px; max-width: 720px; }
</style>
