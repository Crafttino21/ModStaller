<script lang="ts">
  import {
    LayoutGrid, Download, Package, UserRound, Smartphone, ScrollText, Stethoscope, SlidersHorizontal, LoaderCircle,
    Wifi, Usb, Tv, Plus,
  } from "@lucide/svelte";
  import PhoneMockup from "./PhoneMockup.svelte";
  import DeviceIcon from "./DeviceIcon.svelte";
  import BatteryLevel from "./BatteryLevel.svelte";
  import UpdateNotice from "./UpdateNotice.svelte";
  import { go, selectDevice, ui, type View } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";
  import { deviceKind, mockupHeight, osName, overNetwork, transportLabel } from "../lib/device";

  // $derived, damit ein Sprachwechsel die Beschriftungen sofort mitnimmt.
  const items = $derived<{ view: View; label: string; icon: typeof LayoutGrid }[]>([
    { view: "overview", label: t("Overview"), icon: LayoutGrid },
    { view: "install", label: t("Install"), icon: Download },
    { view: "apps", label: t("Apps"), icon: Package },
    { view: "account", label: t("Account"), icon: UserRound },
    { view: "device", label: t("Device"), icon: Smartphone },
    { view: "log", label: t("Log"), icon: ScrollText },
    { view: "system", label: t("System check"), icon: Stethoscope },
    { view: "settings", label: t("Settings"), icon: SlidersHorizontal },
  ]);

  const urgentCount = $derived(ui.status?.urgent.length ?? 0);
  const device = $derived(ui.status?.device);
  /** Die anderen erreichbaren Geraete - zum Umschalten. */
  const others = $derived((ui.status?.devices ?? []).filter((d) => d.udid !== ui.status?.selectedUdid));
  const checkProblems = $derived(ui.checks.list?.filter((c) => c.state === "bad").length ?? 0);
</script>

<aside>
  <div class="brand">
    <div class="logo">
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <defs>
          <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#8b6cff" />
            <stop offset="1" stop-color="#3ec9f0" />
          </linearGradient>
        </defs>
        <rect x="3" y="3" width="26" height="26" rx="8" fill="url(#lg)" />
        <path d="M11 20.5V11.5l5 5.2 5-5.2v9" fill="none" stroke="#fff" stroke-width="2.4"
              stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
    <div>
      <div class="name">ModStaller</div>
      <div class="sub">{t("Sideloading for {platform}", { platform: window.backend.platform === "win32" ? "Windows" : "Linux" })}</div>
    </div>
  </div>

  <nav>
    {#each items as item (item.view)}
      <button class:active={ui.view === item.view} onclick={() => go(item.view)}>
        <item.icon size={18} strokeWidth={2} />
        <span>{item.label}</span>
        {#if item.view === "apps" && urgentCount}
          <span class="badge">{urgentCount}</span>
        {/if}
        {#if item.view === "device" && checkProblems}
          <span class="badge bad">{checkProblems}</span>
        {/if}
        {#if item.view === "account" && ui.status && !ui.status.loggedIn}
          <span class="badge warn">!</span>
        {/if}
      </button>
    {/each}
  </nav>

  <div class="foot">
    <UpdateNotice />
    {#if ui.task?.state === "running" && !ui.task.open}
      <button class="running" onclick={() => ui.task && (ui.task.open = true)}>
        <LoaderCircle size={15} class="spin" />
        <span>{ui.task.title}</span>
      </button>
    {/if}
    {#if device}
      <button class="device" onclick={() => go("device")} title={t("Go to device")}>
        <PhoneMockup form={device.formFactor} height={mockupHeight(device, 58)} />
        <div class="dev-info">
          <div class="dev-name">{device.name}</div>
          <div class="dev-model">{device.model || deviceKind(device)}</div>
          <div class="dev-meta">
            <span class="os">{osName(device)} {device.iosVersion}</span>
            <span class="via" title={transportLabel(device)}>
              {#if overNetwork(device)}<Wifi size={13} />{:else}<Usb size={13} />{/if}
            </span>
            {#if device.battery}<BatteryLevel level={device.battery.level} charging={device.battery.charging} />{/if}
          </div>
        </div>
      </button>
    {:else}
      <div class="conn">
        {#if ui.status?.deviceAttached}
          <span class="dot" style:color="var(--warn)"></span>
          <span>{t("Connected but not ready")}</span>
        {:else}
          <span class="dot" style:color="var(--text-3)"></span>
          <span class="faint">{t("No device")}</span>
        {/if}
      </div>
    {/if}
    {#if others.length}
      <div class="others">
        {#each others as d (d.udid)}
          <button class="other" onclick={() => selectDevice(d.udid)} title={t("Switch to this device")}>
            <DeviceIcon platform={d.platform} formFactor={d.formFactor} size={15} />
            <span class="other-name">{d.name}</span>
            {#if overNetwork(d)}<Wifi size={13} class="faint" />{:else}<Usb size={13} class="faint" />{/if}
          </button>
        {/each}
      </div>
    {/if}
    <button class="other add" onclick={() => (ui.pairingOpen = true)} title={t("Pair Apple TV or Vision Pro")}>
      <Plus size={15} /><span class="other-name">{t("Pair device")}</span>
    </button>
  </div>
</aside>

<style>
  aside {
    width: 232px;
    min-width: 0;
    flex: none;
    display: flex;
    flex-direction: column;
    padding: 18px 12px 14px;
    background: var(--bg-elev);
    border-right: 1px solid var(--border);
  }
  .brand { display: flex; align-items: center; gap: 11px; padding: 4px 8px 22px; }
  .logo svg { width: 34px; height: 34px; display: block; filter: drop-shadow(0 4px 12px rgb(110 100 255 / 0.35)); }
  .name { font-weight: 700; font-size: 15px; letter-spacing: -0.01em; }
  .sub { font-size: 11.5px; color: var(--text-3); }

  nav { display: grid; gap: 2px; }
  nav button {
    display: flex;
    align-items: center;
    gap: 11px;
    height: 38px;
    padding: 0 12px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: var(--text-2);
    font: inherit;
    font-weight: 520;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s, color 0.15s;
  }
  nav button:hover { background: var(--surface-2); color: var(--text); }
  nav button.active { background: var(--accent-soft); color: var(--text); }
  nav button.active :global(svg) { color: var(--accent); }
  nav button span:first-of-type { flex: 1; }

  .badge {
    min-width: 19px;
    height: 19px;
    padding: 0 6px;
    border-radius: 999px;
    background: var(--warn);
    color: #1b1400;
    font-size: 11px;
    font-weight: 700;
    display: grid;
    place-items: center;
  }

  .badge.bad { background: var(--bad); color: #fff; }
  /* minmax(0, 1fr): sonst waechst die Spalte mit dem breitesten Inhalt mit
     (lange Uebersetzungen, Geraetezeile) und schiebt ihn aus der Sidebar. */
  .foot { margin-top: auto; display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; }
  .running {
    display: flex; align-items: center; gap: 8px;
    padding: 9px 12px; border-radius: 10px;
    border: 1px solid var(--border); background: var(--surface);
    color: var(--text); font: inherit; font-size: 12.5px; cursor: pointer; text-align: left;
  }
  .running span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .conn { display: flex; align-items: center; gap: 9px; padding: 8px 12px; font-size: 12.5px; color: var(--text-2); }
  .device {
    display: flex; align-items: center; gap: 12px; width: 100%; min-width: 0; overflow: hidden;
    padding: 10px 12px; border-radius: 12px;
    border: 1px solid var(--border); background: var(--surface);
    color: inherit; font: inherit; text-align: left; cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }
  .device:hover { border-color: var(--border-strong); background: var(--surface-2); }
  .dev-info { min-width: 0; flex: 1; display: grid; gap: 1px; }
  .dev-name { font-weight: 600; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dev-model { font-size: 12px; color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dev-meta { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-top: 3px;
              font-size: 12px; color: var(--text-3); }
  .via { display: inline-flex; flex: none; color: var(--text-3); }
  .os { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dev-meta :global(svg) { flex: none; }
  .other :global(svg) { flex: none; }
  .others { display: grid; grid-template-columns: minmax(0, 1fr); gap: 2px; }
  .other {
    display: flex; align-items: center; gap: 9px; width: 100%;
    padding: 7px 12px; border-radius: 9px; border: 1px solid transparent;
    background: transparent; color: var(--text-2); font: inherit; font-size: 12.5px;
    text-align: left; cursor: pointer;
  }
  .other:hover { background: var(--surface-2); color: var(--text); border-color: var(--border); }
  .add { color: var(--text-3); }
  .other-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
