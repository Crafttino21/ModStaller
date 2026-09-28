<script lang="ts">
  // Linux-Setup: installiert ModStaller fest ins Benutzerprofil (Startmenue,
  // `modstaller` im Terminal, Updates ueber eine neue Setup-AppImage). Die
  // Arbeit macht electron/linux-install.cjs im Hauptprozess; hier wird nur
  // gefragt und angezeigt.
  //
  // Mit --update (vom Updater der installierten App) laeuft alles ohne
  // Rueckfrage durch und die neue Version startet danach selbst.
  import {
    Check, Download, FolderOpen, LoaderCircle, Monitor, Rocket, Trash2, TriangleAlert,
    Languages, Terminal,
  } from "@lucide/svelte";
  import { LANGUAGES, locale, setLocale, t } from "../lib/i18n.svelte";
  import type { SetupInfo, SetupResult } from "../lib/types";

  const setup = window.setup!;

  type Step = "choose" | "working" | "done" | "removed" | "error";

  let info = $state<SetupInfo | null>(null);
  let step = $state<Step>("choose");
  let percent = $state(0);
  let result = $state<SetupResult | null>(null);
  let error = $state("");
  let desktopShortcut = $state(true);
  let confirmRemove = $state(false);
  let purge = $state(false);
  let working = $state<"install" | "uninstall">("install");

  const sameVersion = $derived(info?.installed === info?.version);

  setup.onProgress((p) => (percent = p.percent));

  setup.info().then((i) => {
    info = i;
    if (setup.autoUpdate) install();
  }, (err) => fail(err));

  function fail(err: unknown) {
    error = String((err as Error)?.message ?? err).replace(/^Error invoking remote method '[^']+': (Error: )?/, "");
    step = "error";
  }

  async function install() {
    working = "install";
    step = "working";
    percent = 0;
    try {
      result = await setup.install(setup.autoUpdate
        ? {}                                        // Update: nichts umstellen
        : { language: locale(), desktopShortcut: info?.installed ? undefined : desktopShortcut });
      step = "done";
      if (setup.autoUpdate) {
        if (info?.launchAfter) await setup.launch();
        else await setup.quit();
      }
    } catch (err) {
      fail(err);
    }
  }

  async function uninstall() {
    working = "uninstall";
    step = "working";
    try {
      await setup.uninstall({ purge });
      step = "removed";
    } catch (err) {
      fail(err);
    }
  }
</script>

<main class="setup">
  <header>
    <div class="logo"><Download size={22} /></div>
    <div>
      <h1>{t("ModStaller Setup")}</h1>
      <p class="muted">{info ? t("Version {version} for Linux", { version: info.version }) : ""}</p>
    </div>
  </header>

  {#if !info && step !== "error"}
    <div class="center"><LoaderCircle class="spin" size={26} /></div>

  {:else if step === "choose" && info}
    <section class="card pad">
      <h2><Languages size={17} /> {t("Language")}</h2>
      <div class="langs">
        {#each LANGUAGES as l (l.code)}
          <button class="lang" class:active={l.code === locale()} onclick={() => setLocale(l.code)}>
            <span class="name">{l.name}</span>
            {#if l.code === locale()}<Check size={15} />{/if}
          </button>
        {/each}
      </div>
    </section>

    <section class="card pad">
      <h2><FolderOpen size={17} /> {t("Where ModStaller is installed")}</h2>
      <p class="muted desc">{t("Only for your user – no administrator rights needed. Your sign-ins and settings stay where they are.")}</p>
      <dl>
        <dt>{t("Program")}</dt><dd class="mono selectable">{info.paths.app}</dd>
        <dt>{t("Start menu")}</dt><dd class="mono selectable">{info.paths.desktop}</dd>
        <dt>{t("Terminal")}</dt><dd class="mono selectable">{info.paths.cli}</dd>
      </dl>

      {#if !info.installed}
        <label class="check">
          <input type="checkbox" bind:checked={desktopShortcut} />
          <Monitor size={16} /> {t("Create a desktop shortcut")}
        </label>
      {/if}
    </section>

    {#if info.installed}
      <div class="banner info">
        <Check size={18} color="var(--accent)" />
        <div class="grow">{t("ModStaller {version} is already installed.", { version: info.installed })}</div>
      </div>
    {/if}

    <div class="actions">
      {#if info.installed}
        <button class="btn danger" onclick={() => (confirmRemove = !confirmRemove)}>
          <Trash2 size={16} /> {t("Uninstall")}
        </button>
      {/if}
      <span class="grow"></span>
      <button class="btn primary" onclick={install}>
        <Download size={16} />
        {!info.installed ? t("Install") : sameVersion ? t("Repair") : t("Update to {version}", { version: info.version })}
      </button>
    </div>

    {#if confirmRemove}
      <section class="card pad remove">
        <p>{t("Removes the program, the start menu entry and the `modstaller` command.")}</p>
        <label class="check">
          <input type="checkbox" bind:checked={purge} />
          {t("Also delete sign-ins, settings and logs")}
        </label>
        <div class="actions">
          <span class="grow"></span>
          <button class="btn" onclick={() => (confirmRemove = false)}>{t("Cancel")}</button>
          <button class="btn danger" onclick={uninstall}><Trash2 size={16} /> {t("Uninstall now")}</button>
        </div>
      </section>
    {/if}

  {:else if step === "working"}
    <section class="card pad center-col">
      <LoaderCircle class="spin" size={28} />
      <p>{working === "uninstall" ? t("Removing ModStaller…") : t("Installing ModStaller…")}</p>
      {#if working === "install"}
        <div class="bar"><div style="width: {percent}%"></div></div>
        <p class="faint small">{percent} %</p>
      {/if}
    </section>

  {:else if step === "done" && result}
    <section class="card pad center-col">
      <div class="ok"><Check size={28} /></div>
      <h2>{t("ModStaller {version} is installed.", { version: result.version })}</h2>
      <p class="muted">{t("You find it in the start menu. You can remove it again by running this setup once more.")}</p>
    </section>
    {#if !result.cli}
      <div class="banner warn">
        <TriangleAlert size={18} color="var(--warn)" />
        <div class="grow">{t("There already is a different `modstaller` command in ~/.local/bin – it was left untouched.")}</div>
      </div>
    {:else if !result.binOnPath}
      <div class="banner info">
        <Terminal size={18} color="var(--accent)" />
        <div class="grow">{t("~/.local/bin is not on your PATH yet – the `modstaller` command works in the terminal after logging in again.")}</div>
      </div>
    {/if}
    <div class="actions">
      <span class="grow"></span>
      <button class="btn" onclick={() => setup.quit()}>{t("Close")}</button>
      <button class="btn primary" onclick={() => setup.launch()}><Rocket size={16} /> {t("Start ModStaller")}</button>
    </div>

  {:else if step === "removed"}
    <section class="card pad center-col">
      <div class="ok"><Check size={28} /></div>
      <h2>{t("ModStaller was removed.")}</h2>
      {#if !purge}<p class="muted">{t("Your sign-ins and settings were kept.")}</p>{/if}
    </section>
    <div class="actions">
      <span class="grow"></span>
      <button class="btn primary" onclick={() => setup.quit()}>{t("Close")}</button>
    </div>

  {:else if step === "error"}
    <div class="banner bad">
      <TriangleAlert size={18} color="var(--bad)" />
      <div class="grow selectable">{error}</div>
    </div>
    <div class="actions">
      <span class="grow"></span>
      <button class="btn" onclick={() => setup.quit()}>{t("Close")}</button>
      <button class="btn primary" onclick={() => { step = "choose"; if (!info) setup.info().then((i) => (info = i), fail); }}>
        {t("Try again")}
      </button>
    </div>
  {/if}
</main>

<style>
  .setup { max-width: 700px; margin: 0 auto; padding: 26px 22px 30px; display: grid; gap: 14px; }
  header { display: flex; align-items: center; gap: 14px; }
  .logo { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
          background: var(--accent-grad); color: #fff; flex: none; }
  h1 { font-size: 20px; }
  h2 { display: flex; align-items: center; gap: 8px; font-size: 15.5px; }
  .pad { padding: 18px 20px; }
  .desc { margin-top: 6px; font-size: 13px; }
  .langs { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 7px; margin-top: 12px; }
  .lang { display: flex; align-items: center; gap: 8px; padding: 9px 12px; border-radius: 10px;
          border: 1px solid var(--border-strong); background: var(--surface-2); color: var(--text);
          font: inherit; cursor: pointer; text-align: left; }
  .lang:hover { border-color: var(--text-3); }
  .lang.active { border-color: var(--accent); background: var(--accent-soft); }
  .name { flex: 1; min-width: 0; font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 6px 14px; margin-top: 12px; font-size: 13px; }
  dt { color: var(--text-2); }
  dd { margin: 0; overflow-wrap: anywhere; }
  .mono { font-family: var(--mono); font-size: 12px; }
  .check { display: flex; align-items: center; gap: 9px; margin-top: 14px; cursor: pointer; font-size: 13.5px; }
  .actions { display: flex; align-items: center; gap: 10px; }
  .grow { flex: 1; min-width: 0; }
  .remove p { font-size: 13.5px; }
  .remove .actions { margin-top: 14px; }
  .center { display: grid; place-items: center; padding: 60px 0; }
  .center-col { display: grid; justify-items: center; gap: 10px; text-align: center; padding: 30px 20px; }
  .ok { width: 52px; height: 52px; border-radius: 50%; display: grid; place-items: center;
        background: var(--ok-soft); color: var(--ok); }
  .bar { width: 100%; max-width: 420px; height: 8px; border-radius: 99px; background: var(--border); overflow: hidden; }
  .bar > div { height: 100%; background: var(--accent-grad); transition: width 0.2s; }
  .small { font-size: 12px; }
</style>
