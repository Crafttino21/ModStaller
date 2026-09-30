<script lang="ts">
  import { X, Download, SlidersHorizontal, LoaderCircle, ArrowUpCircle, TriangleAlert, ShieldAlert } from "@lucide/svelte";
  import { warningText } from "../lib/store";
  import Modal from "./Modal.svelte";
  import StoreImage from "./StoreImage.svelte";
  import { ask, busy, errorText, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { mb } from "../lib/format";
  import { storeCustomize, storeInstall, storeUpdate } from "../lib/actions";
  import { t } from "../lib/i18n.svelte";
  import type { Device, StoreApp, StoreAppDetail, StoreUpdate } from "../lib/types";
  import { deviceKind, storeDevice } from "../lib/device";

  let { app, sourceName, update, installed, device = null, onclose }: {
    app: StoreApp; sourceName: (url: string) => string; update?: StoreUpdate; installed: boolean;
    device?: Device | null; onclose: () => void;
  } = $props();

  let detail = $state<StoreAppDetail | null>(null);
  let error = $state("");
  let version = $state("");
  /** Aus welcher Quelle geladen wird - die App gibt es oft in mehreren. */
  let source = $state("");

  $effect(() => {
    source = app.source;
  });

  $effect(() => {
    const bundleId = app.bundleId;
    const from = source;
    if (!from) return;
    detail = null;
    error = "";
    let stale = false;
    call<StoreAppDetail>("store.app", { source: from, bundleId, device: storeDevice(device) }).then(
      (d) => { if (!stale) { detail = d; version = d.versions[0]?.version ?? d.version; } },
      (err) => { if (!stale) error = errorText(err); },
    );
    return () => { stale = true; };
  });

  const chosen = $derived(detail?.versions.find((v) => v.version === version));
  const noDevice = $derived(!ui.status?.device);
  const latest = $derived(!detail || version === detail.versions[0]?.version);

  const chosenApp = $derived({ ...app, source });

  function families(f: number[]): string {
    const names: Record<number, string> = { 1: "iPhone", 2: "iPad", 3: "Apple TV", 7: "Vision Pro" };
    return f.map((x) => names[x]).filter(Boolean).join(", ");
  }

  /** Vor riskanten Apps einmal nachfragen. */
  async function confirmed(): Promise<boolean> {
    const warning = detail?.warning || app.warning;
    if (!warning) return true;
    const { ok } = await ask({
      title: t("Install {name}?", { name: app.name }),
      text: warningText(warning),
      confirm: t("Install anyway"),
      danger: true,
    });
    return ok;
  }

  async function install() {
    if (!(await confirmed())) return;
    onclose();
    storeInstall(chosenApp, latest ? undefined : version);
  }

  async function customize() {
    if (!(await confirmed())) return;
    onclose();
    storeCustomize(chosenApp, latest ? undefined : version);
  }

  function doUpdate() {
    if (!update) return;
    onclose();
    storeUpdate(update);
  }
</script>

<Modal width={640} {onclose}>
  <div class="head">
    <StoreImage url={app.iconUrl} fallback={app.name} class="big-icon" />
    <div class="grow">
      <h2>{app.name}</h2>
      <p class="muted">{app.developer || sourceName(source)}</p>
      <p class="faint small">{t("From {source}", { source: sourceName(source) })}</p>
    </div>
    <button class="btn icon ghost" title={t("Close")} onclick={onclose}><X size={18} /></button>
  </div>

  {#if detail?.warning || app.warning}
    <div class="banner bad warnbox">
      <TriangleAlert size={18} color="var(--bad)" />
      <div class="grow small">{warningText(detail?.warning || app.warning)}</div>
    </div>
  {/if}

  {#if device && detail?.compatible === false}
    <div class="banner warn warnbox">
      <TriangleAlert size={18} color="var(--warn)" />
      <div class="grow small">{t("This version does not fit the {kind} ({name}) - check the required system version and device type, or pick another source.", { kind: deviceKind(device), name: device.name })}</div>
    </div>
  {/if}

  {#if detail && detail.offers.length > 1}
    <label class="pick">
      <span class="faint small">{t("Source")}</span>
      <select bind:value={source}>
        {#each detail.offers as o (o.source)}
          <option value={o.source}>{sourceName(o.source)} – {o.version}</option>
        {/each}
      </select>
    </label>
  {/if}

  <div class="facts">
    <div><span class="faint">{t("Version")}</span><b>{chosen?.version ?? app.version}</b></div>
    <div><span class="faint">{t("Size")}</span><b>{mb(chosen?.size || app.size)}</b></div>
    {#if chosen?.min_os || detail?.minOs || app.minOs}<div><span class="faint">{t("Requires")}</span><b>iOS {chosen?.min_os || detail?.minOs || app.minOs}</b></div>{/if}
    {#if detail?.families.length}<div><span class="faint">{t("Runs on")}</span><b>{families(detail.families)}</b></div>{/if}
    {#if chosen?.date || app.date}<div><span class="faint">{t("Released")}</span><b>{(chosen?.date || app.date).slice(0, 10)}</b></div>{/if}
  </div>

  <!-- Fuer jede App, nicht nur die markierten: niemand prueft, was eine
       Quelle ausliefert. -->
  <p class="aware">
    <ShieldAlert size={14} />
    <span>{t("Sideloading has risks: apps from sources are not reviewed by Apple. Only install apps from sources you trust, and keep an eye on what an app asks for.")}</span>
  </p>

  <div class="actions">
    {#if update}
      <button class="btn primary" disabled={busy() || noDevice} onclick={doUpdate}>
        <ArrowUpCircle size={16} /> {t("Update to {version}", { version: update.offered })}
      </button>
    {:else}
      <button class="btn primary" disabled={busy() || noDevice} onclick={install}>
        <Download size={16} /> {installed ? t("Reinstall") : t("Install")}
      </button>
    {/if}
    <button class="btn" disabled={busy()} onclick={customize}>
      <SlidersHorizontal size={16} /> {t("Customize …")}
    </button>
    {#if detail && detail.versions.length > 1}
      <select bind:value={version} class="ver">
        {#each detail.versions as v (v.version)}<option value={v.version}>{v.version}</option>{/each}
      </select>
    {/if}
  </div>
  {#if noDevice}<p class="faint small">{t("Connect a device to install.")}</p>{/if}

  {#if error}
    <p class="bad-text small selectable">{error}</p>
  {:else if !detail}
    <div class="loading"><LoaderCircle size={20} class="spin" /></div>
  {:else}
    {#if detail.screenshots.length}
      <div class="shots">
        {#each detail.screenshots as s (s)}<StoreImage url={s} kind="screenshot" class="shot" />{/each}
      </div>
    {/if}
    {#if detail.subtitle}<p class="subtitle">{detail.subtitle}</p>{/if}
    {#if detail.description}<p class="desc selectable">{detail.description}</p>{/if}
    {#if chosen?.notes}
      <h3>{t("What's new in {version}", { version: chosen.version })}</h3>
      <p class="desc selectable">{chosen.notes}</p>
    {/if}
    <p class="faint tiny mono selectable">{app.bundleId}</p>
  {/if}
</Modal>

<style>
  .head { display: flex; gap: 14px; align-items: center; }
  .warnbox { margin-top: 14px; }
  .aware { display: flex; gap: 8px; align-items: flex-start; margin: 0 0 12px; padding: 9px 12px;
           border-radius: 10px; background: var(--surface-2); color: var(--text-2); font-size: 12.5px; }
  .aware :global(svg) { flex: none; margin-top: 1px; color: var(--text-3); }
  .pick { display: flex; align-items: center; gap: 10px; margin-top: 14px; }
  .pick select { height: 34px; width: auto; min-width: 220px; }
  .head :global(.big-icon) { width: 72px; height: 72px; border-radius: 17px; }
  .head h2 { font-size: 20px; }
  .grow { flex: 1; min-width: 0; }
  .facts { display: flex; flex-wrap: wrap; gap: 8px 22px; margin: 16px 0; font-size: 13px; }
  .facts div { display: grid; gap: 2px; }
  .actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .ver { height: 34px; width: auto; min-width: 110px; margin-left: auto; }
  .shots { display: flex; gap: 10px; overflow-x: auto; margin: 18px 0 6px; padding-bottom: 6px; }
  .shots :global(.shot) { height: 320px; min-width: 150px; border-radius: 12px; }
  .subtitle { margin-top: 12px; font-weight: 550; }
  /* Fremder Text - nur als Text, mit seinen Zeilenumbruechen. */
  .desc { margin-top: 8px; white-space: pre-wrap; font-size: 13.5px; color: var(--text-2); }
  h3 { margin-top: 16px; font-size: 14px; }
  .loading { display: grid; place-items: center; padding: 24px; color: var(--accent); }
  .small { font-size: 12.5px; margin-top: 6px; }
  .tiny { font-size: 11.5px; margin-top: 14px; }
  .bad-text { color: var(--bad); }
</style>
