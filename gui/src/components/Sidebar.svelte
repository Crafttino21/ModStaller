<script lang="ts">
  import {
    LayoutGrid, Download, Package, UserRound, Smartphone, Stethoscope, SlidersHorizontal, LoaderCircle,
  } from "@lucide/svelte";
  import PhoneMockup from "./PhoneMockup.svelte";
  import BatteryLevel from "./BatteryLevel.svelte";
  import UpdateNotice from "./UpdateNotice.svelte";
  import { go, ui, type View } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";

  // $derived, damit ein Sprachwechsel die Beschriftungen sofort mitnimmt.
  const items = $derived<{ view: View; label: string; icon: typeof LayoutGrid }[]>([
    { view: "overview", label: t("Overview"), icon: LayoutGrid },
    { view: "install", label: t("Install"), icon: Download },
    { view: "apps", label: t("Apps"), icon: Package },
    { view: "account", label: t("Account"), icon: UserRound },
    { view: "device", label: t("Device"), icon: Smartphone },
    { view: "system", label: t("System check"), icon: Stethoscope },
    { view: "settings", label: t("Settings"), icon: SlidersHorizontal },
  ]);

  const urgentCount = $derived(ui.status?.urgent.length ?? 0);
  const device = $derived(ui.status?.device);
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
        <PhoneMockup form={device.formFactor} height={58} />
        <div class="dev-info">
          <div class="dev-name">{device.name}</div>
          <div class="dev-model">{device.model}</div>
          <div class="dev-meta">
            <span>iOS {device.iosVersion}</span>
            {#if device.battery}<BatteryLevel level={device.battery.level} charging={device.battery.charging} />{/if}
          </div>
        </div>
      </button>
    {:else}
      <div class="conn">
        {#if ui.status?.deviceAttached}
          <span class="dot" style:color="var(--warn)"></span>
          <span>iPhone gesperrt?</span>
        {:else}
          <span class="dot" style:color="var(--text-3)"></span>
          <span class="faint">{t("No iPhone")}</span>
        {/if}
      </div>
    {/if}
  </div>
</aside>

<style>
  aside {
    width: 232px;
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
  .foot { margin-top: auto; display: grid; gap: 8px; }
  .running {
    display: flex; align-items: center; gap: 8px;
    padding: 9px 12px; border-radius: 10px;
    border: 1px solid var(--border); background: var(--surface);
    color: var(--text); font: inherit; font-size: 12.5px; cursor: pointer; text-align: left;
  }
  .running span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .conn { display: flex; align-items: center; gap: 9px; padding: 8px 12px; font-size: 12.5px; color: var(--text-2); }
  .device {
    display: flex; align-items: center; gap: 12px; width: 100%;
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
</style>
