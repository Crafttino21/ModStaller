<script lang="ts">
  import { LoaderCircle } from "@lucide/svelte";
  import Sidebar from "./components/Sidebar.svelte";
  import TaskPanel from "./components/TaskPanel.svelte";
  import TwoFactor from "./components/TwoFactor.svelte";
  import ConfirmDialog from "./components/ConfirmDialog.svelte";
  import Toasts from "./components/Toasts.svelte";
  import BackendDown from "./components/BackendDown.svelte";
  import Overview from "./views/Overview.svelte";
  import Install from "./views/Install.svelte";
  import Apps from "./views/Apps.svelte";
  import Account from "./views/Account.svelte";
  import Device from "./views/Device.svelte";
  import System from "./views/System.svelte";
  import { go, toast, ui } from "./lib/state.svelte";

  const views = { overview: Overview, install: Install, apps: Apps, account: Account, device: Device, system: System };
  const View = $derived(views[ui.view]);

  // Eine IPA darf ueberall ins Fenster fallen, nicht nur auf die Drop-Zone.
  function dragover(e: DragEvent) {
    e.preventDefault();
  }
  function drop(e: DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer?.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".ipa")) {
      toast("Das ist keine IPA-Datei.", "warn");
      return;
    }
    ui.droppedIpa = window.backend.pathForFile(file);
    go("install");
  }
</script>

<svelte:window ondragover={dragover} ondrop={drop} />

<div class="shell">
  <Sidebar />
  <main>
    {#if ui.backend === "down"}
      <BackendDown />
    {:else if ui.backend === "starting"}
      <div class="boot"><LoaderCircle size={28} class="spin" /><p class="muted">ModStaller startet …</p></div>
    {:else}
      <div class="page">
        {#key ui.view}<View />{/key}
      </div>
    {/if}
  </main>
</div>

{#if ui.task?.open}<TaskPanel />{/if}
{#if ui.twoFactor}<TwoFactor />{/if}
{#if ui.confirm}<ConfirmDialog />{/if}
<Toasts />

<style>
  .shell { display: flex; height: 100%; }
  main { flex: 1; min-width: 0; overflow: auto; }
  .page { max-width: 1080px; margin: 0 auto; padding: 34px 36px 48px; animation: in 0.2s ease; }
  @keyframes in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  .boot { height: 100%; display: grid; place-content: center; justify-items: center; gap: 12px; color: var(--accent); }
</style>
