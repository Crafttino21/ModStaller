<script lang="ts">
  // Windows ohne Apple-Geraetedienst: der Explorer zeigt das iPhone ueber den
  // Windows-eigenen Fototreiber, ModStaller sieht es nie. Das muss hier
  // stehen - "nicht verbunden" waere schlicht falsch.
  import { TriangleAlert, ExternalLink, Wand, Play } from "@lucide/svelte";
  import { busy, ui } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";
  import { setupUsbService } from "../lib/actions";

  /** Die Seite der App "Apple Devices" (Apple-Geraete) im Microsoft Store. */
  const STORE_URL = "https://apps.microsoft.com/detail/9NP83LWLPZ9K";

  /** Auch den Tipp fuer "Dienst da, iPhone trotzdem nicht" zeigen - nur auf
   *  der Geraeteseite, sonst stuende er bei jedem ohne eingestecktes iPhone. */
  let { stuckHint = false }: { stuckHint?: boolean } = $props();

  const missing = $derived(ui.status?.usbService === "missing");
  const stopped = $derived(ui.status?.usbService === "stopped");
  // Dienst laeuft, aber kein Geraet: meist haengt das iPhone noch am
  // Windows-Fototreiber (z. B. vor Apple Devices eingesteckt).
  const stuck = $derived(
    stuckHint &&
      window.backend.platform === "win32" &&
      ui.status?.usbService === "ok" &&
      !ui.status?.deviceAttached,
  );
</script>

{#if missing}
  <div class="banner bad">
    <TriangleAlert size={20} color="var(--bad)" />
    <div class="grow">
      <strong>{t("Apple device service missing")}</strong>
      <div class="muted small">
        {t("Windows shows the iPhone in Explorer through its own photo driver – ModStaller needs Apple’s device service for USB. ModStaller can set it up for you: “Apple Devices” from the Microsoft Store, otherwise just Apple’s USB driver.")}
      </div>
    </div>
    <div class="buttons">
      <button class="btn sm primary" disabled={busy()} onclick={setupUsbService}>
        <Wand size={15} /> {t("Set up automatically")}
      </button>
      <a class="btn sm" href={STORE_URL} target="_blank" rel="noreferrer">
        <ExternalLink size={15} /> {t("Microsoft Store")}
      </a>
    </div>
  </div>
{:else if stopped}
  <div class="banner warn">
    <TriangleAlert size={20} color="var(--warn)" />
    <div class="grow">
      <strong>{t("Apple device service is not running")}</strong>
      <div class="muted small">
        {t("It is installed but stopped. Windows asks for confirmation once when it is started.")}
      </div>
    </div>
    <button class="btn sm primary" disabled={busy()} onclick={setupUsbService}>
      <Play size={15} /> {t("Start service")}
    </button>
  </div>
{:else if stuck}
  <p class="faint small hint">
    {t("Explorer shows the iPhone but ModStaller doesn’t? Unplug it, unlock it and plug it back in – if that doesn’t help, restart the PC.")}
  </p>
{/if}

<style>
  .banner { margin-bottom: 16px; }
  .hint { margin: 0 0 16px; }
  a.btn { text-decoration: none; }
  .btn { white-space: nowrap; }
  .buttons { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
</style>
