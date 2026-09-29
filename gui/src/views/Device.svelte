<script lang="ts">
  import { Smartphone, TriangleAlert, Search, LoaderCircle, RefreshCw, Wifi, Usb, Tv } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import DeviceChecks from "../components/DeviceChecks.svelte";
  import UsbServiceBanner from "../components/UsbServiceBanner.svelte";
  import { busy, errorText, onDevice, refreshStatus, ui } from "../lib/state.svelte";
  import { forgetDevice, setWifi } from "../lib/actions";
  import { deviceKind, osName, transportLabel } from "../lib/device";
  import { call } from "../lib/rpc";
  import type { DeviceApp, DeviceInfo } from "../lib/types";
  import { t } from "../lib/i18n.svelte";

  let info = $state<DeviceInfo | null>(null);
  let error = $state("");
  let apps = $state<DeviceApp[] | null>(null);
  let appsLoading = $state(false);
  let filter = $state("");

  const connected = $derived(!!ui.status?.device);
  const selected = $derived(ui.status?.device?.udid ?? null);

  async function load() {
    error = "";
    try {
      info = await call<DeviceInfo>("device.info", onDevice({}));
    } catch (err) {
      info = null;
      error = errorText(err);
    }
  }

  async function loadApps() {
    appsLoading = true;
    try {
      apps = await call<DeviceApp[]>("device.apps", onDevice({}));
    } catch (err) {
      error = errorText(err);
    } finally {
      appsLoading = false;
    }
  }

  // Beim An- und Abstecken und beim Wechsel des Geraets neu laden.
  $effect(() => {
    if (selected) {
      info = null;
      apps = null;
      load();
    } else { info = null; apps = null; }
  });

  const shown = $derived(
    (apps ?? []).filter((a) => !filter || `${a.name} ${a.bundleId}`.toLowerCase().includes(filter.toLowerCase())),
  );
</script>

<PageHeader title={t("Device")} subtitle={ui.status?.device
  ? t("{kind} via {via}", { kind: deviceKind(ui.status.device), via: transportLabel(ui.status.device) })
  : t("The connected device.")} />

{#if ui.status?.deviceAttached}
  <div class="checks"><DeviceChecks /></div>
{/if}

{#if !connected}
  <UsbServiceBanner stuckHint />
  <div class="card empty">
    <Smartphone size={30} />
    <p>{ui.status?.deviceAttached ? t("Connected but not ready – unlock the iPhone and confirm “Trust”.") : t("No device connected. Plug the iPhone in via USB and unlock it – or bring it into the same Wi-Fi.")}</p>
    {#if ui.status?.error && (ui.status.usbService ?? "ok") === "ok"}<p class="faint small selectable">{ui.status.error}</p>{/if}
    <button class="btn sm" onclick={() => (ui.pairingOpen = true)}><Tv size={15} /> {t("Pair Apple TV")}</button>
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
        <div class="phone">{#if info.platform === "tvos"}<Tv size={30} />{:else}<Smartphone size={30} />{/if}</div>
        <div>
          <h2>{info.name}</h2>
          <p class="muted">{info.productType} · {osName(info)} {info.iosVersion} ({info.build}) · {transportLabel(info)}</p>
        </div>
      </div>
      <dl>
        <dt>UDID</dt><dd class="mono selectable">{info.udid}</dd>
        <dt>{t("Developer Mode")}</dt>
        <dd>
          {#if info.developerMode}<span class="chip ok"><span class="dot"></span>{t("on")}</span>
          {:else}<span class="chip bad"><span class="dot"></span>{t("off")}</span>
            <span class="muted small">{t("Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.")}</span>{/if}
        </dd>
      </dl>
    {/if}
  </div>

  {#if ui.status?.device}
    {@const d = ui.status.device}
    <div class="card pad">
      <h2 class="conn-head">{#if d.transport === "usb"}<Usb size={18} />{:else}<Wifi size={18} />{/if} {t("Connection")}</h2>
      {#if d.platform === "tvos"}
        <p class="muted small">{t("Paired by PIN – reachable while the Apple TV is on and in the same network.")}</p>
      {:else if d.transport === "usb"}
        <p class="muted small">{d.wifiEnabled
          ? t("Connected via USB. Wi-Fi is on – without the cable ModStaller finds the iPhone in the same network.")
          : t("Connected via USB. With Wi-Fi switched on, ModStaller also reaches the iPhone without the cable – for installing, renewing and the automatic renewal in the tray.")}</p>
      {:else}
        <p class="muted small">{t("Connected via Wi-Fi. For JIT below iOS 17.4 the cable is still needed.")}</p>
      {/if}
      <div class="conn-actions">
        {#if d.platform !== "tvos" && !d.wifiEnabled}
          <button class="btn sm primary" disabled={busy() || d.transport !== "usb"} onclick={() => setWifi(d.udid, true)}>
            <Wifi size={15} /> {t("Switch on Wi-Fi")}
          </button>
        {:else if d.platform !== "tvos"}
          <button class="btn sm" disabled={busy()} onclick={() => setWifi(d.udid, false)}>{t("Switch off Wi-Fi")}</button>
        {/if}
        {#if d.wifiEnabled || d.platform === "tvos"}
          <button class="btn sm ghost" disabled={busy()}
                  onclick={async () => { if (await forgetDevice(d.udid, d.name)) refreshStatus(true); }}>
            {t("Forget device")}
          </button>
        {/if}
      </div>
    </div>
  {/if}

  <div class="card pad">
    <div class="apps-head">
      <h2>{t("Installed user apps")}</h2>
      {#if apps}
        <div class="search"><Search size={15} /><input type="search" placeholder={t("Filter")} bind:value={filter} /></div>
        <button class="btn sm icon ghost" title={t("Reload")} onclick={loadApps}><RefreshCw size={15} /></button>
      {/if}
    </div>
    {#if !apps}
      <button class="btn" onclick={loadApps} disabled={appsLoading}>
        {#if appsLoading}<LoaderCircle size={16} class="spin" />{/if} {t("List apps")}
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
  .conn-head { display: flex; align-items: center; gap: 9px; font-size: 17px; margin-bottom: 8px; }
  .conn-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
</style>
