<script lang="ts">
  import {
    Upload, FileArchive, FolderOpen, TriangleAlert, Puzzle, Layers, Box, X, LoaderCircle, Sparkles,
    ImagePlus, RotateCcw, Watch, Trash2, Recycle, Scissors, SlidersHorizontal,
  } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import QuotaMeter from "../components/QuotaMeter.svelte";
  import { busy, errorText, go, onDevice, ui } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";
  import { call } from "../lib/rpc";
  import { mb, relative } from "../lib/format";
  import { installIpa, uninstallApp } from "../lib/actions";
  import type { ExtensionDetail, FoundIpa, InstallPlan, IpaInfo } from "../lib/types";

  let found = $state<FoundIpa[] | null>(null);
  let info = $state<IpaInfo | null>(null);
  let inspecting = $state(false);
  let inspectError = $state("");
  let dragging = $state(false);
  /** adsid - leer heisst: der aktive Account. */
  let account = $state("");
  const accounts = $derived(ui.status?.accounts ?? []);

  // -- Editor ----------------------------------------------------------------
  // Leer heisst jeweils: so lassen, wie es im IPA steht.
  let displayName = $state("");
  let bundleId = $state("");
  /** Neues Icon als PNG-data:-URL (1024 x 1024). */
  let icon = $state<string | null>(null);
  /** Welche Extensions bleiben - null bis der Plan die Voreinstellung liefert. */
  let keep = $state<string[] | null>(null);
  /** Eine vorhandene, freie App-ID, unter der die App laufen soll. */
  let spare = $state("");

  /** Wie Apple es verlangt - dasselbe Muster wie modstaller/plan.py. */
  const BUNDLE_ID = /^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/;
  const bundleIdValid = $derived(!bundleId.trim() || BUNDLE_ID.test(bundleId.trim()));

  let plan = $state<InstallPlan | null>(null);
  let planError = $state("");
  let planning = $state(false);

  call<FoundIpa[]>("ipa.find").then((f) => (found = f.sort((a, b) => b.modified - a.modified)), () => (found = []));

  function resetEditor() {
    displayName = "";
    bundleId = "";
    icon = null;
    keep = null;
    spare = "";
    plan = null;
    planError = "";
  }

  async function choose(path: string) {
    info = null;
    inspectError = "";
    resetEditor();
    inspecting = true;
    try {
      info = await call<IpaInfo>("ipa.inspect", { path });
    } catch (err) {
      inspectError = errorText(err);
    } finally {
      inspecting = false;
    }
  }

  async function browse() {
    const path = await window.backend.pickIpa();
    if (path) choose(path);
  }

  // Irgendwo ins Fenster gezogen (App.svelte) - hier uebernehmen.
  $effect(() => {
    if (ui.droppedIpa) {
      const p = ui.droppedIpa;
      ui.droppedIpa = null;
      choose(p);
    }
  });

  function onDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    dragging = false;
    const file = e.dataTransfer?.files[0];
    if (file) choose(window.backend.pathForFile(file));
  }

  // -- Plan: was die Installation kostet ------------------------------------
  // Bei jeder Aenderung neu - kurz verzoegert, damit nicht jeder Tastendruck
  // Apple fragt (der Server puffert die Antworten ohnehin 30 s).
  let planSeq = 0;
  $effect(() => {
    if (!info || !ui.status?.loggedIn) return;
    const params = {
      path: info.path,
      ...(account ? { account } : {}),
      ...(bundleId.trim() && bundleIdValid && !spare ? { bundleId: bundleId.trim() } : {}),
      ...(keep ? { extensions: [...keep] } : {}),
      ...(spare ? { spareAppId: spare } : {}),
    };
    const seq = ++planSeq;
    const timer = setTimeout(async () => {
      planning = true;
      try {
        const p = await call<InstallPlan>("install.plan", onDevice(params));
        if (seq !== planSeq) return;
        plan = p;
        planError = "";
        if (keep === null) keep = [...p.keep];
      } catch (err) {
        if (seq === planSeq) planError = errorText(err);
      } finally {
        if (seq === planSeq) planning = false;
      }
    }, 350);
    return () => clearTimeout(timer);
  });

  // Nach dem Entfernen einer App (Slot frei) den Plan auffrischen.
  let wasBusy = false;
  $effect(() => {
    const now = busy();
    if (wasBusy && !now && info) keep = keep ? [...keep] : keep;
    wasBusy = now;
  });

  function toggle(ext: ExtensionDetail, on: boolean) {
    const cur = keep ?? [];
    keep = on ? [...cur, ext.path] : cur.filter((p) => p !== ext.path);
  }

  /** Was fuer eine Extension - nach NSExtensionPointIdentifier. */
  function kind(point: string): string {
    const p = point.toLowerCase();
    if (p.includes("widget")) return t("Widget");
    if (p.includes("share-services")) return t("Share");
    if (p.includes("safari")) return t("Safari");
    if (p.includes("usernotifications")) return t("Notifications");
    if (p.includes("intents")) return t("Siri & Shortcuts");
    if (p.includes("keyboard")) return t("Keyboard");
    if (p.includes("broadcast")) return t("Screen broadcast");
    if (p.includes("fileprovider")) return t("Files");
    if (p.includes("networkextension")) return t("VPN / network");
    if (p.includes("photo-editing")) return t("Photo editing");
    if (p.includes("ui-services")) return t("Action");
    return t("Extension");
  }

  // -- Icon: quadratisch zuschneiden, 1024 px, PNG ----------------------------
  let iconInput = $state<HTMLInputElement | null>(null);
  let iconError = $state("");

  function pickIcon(e: Event) {
    const file = (e.currentTarget as HTMLInputElement).files?.[0];
    (e.currentTarget as HTMLInputElement).value = "";
    if (!file) return;
    iconError = "";
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const size = 1024;
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = size;
        const ctx = canvas.getContext("2d")!;
        // Mittig zuschneiden (wie "cover"); iOS rundet die Ecken selbst.
        const side = Math.min(img.width, img.height);
        ctx.drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, size, size);
        icon = canvas.toDataURL("image/png");
      };
      img.onerror = () => (iconError = t("That image cannot be read."));
      img.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  }

  const st = $derived(ui.status);
  /** Apple-TV-Apps haben geschichtete Icons - ein PNG ersetzt sie nicht. */
  const tvApp = $derived(info?.platform === "tvos");
  const slotsFull = $derived(!!plan?.isFree && !!plan.slots?.max && plan.slots.used >= plan.slots.max);
  const blockers = $derived.by(() => {
    const out: { text: string; action?: () => void; label?: string }[] = [];
    if (!st) return out;
    if (!st.loggedIn) out.push({ text: t("Not signed in with Apple."), action: () => go("account"), label: t("Sign in") });
    if (!st.device && st.deviceAttached)
      out.push({ text: t("The iPhone is plugged in but locked or not paired."), action: () => go("device"), label: t("Fix") });
    else if (!st.device) out.push({ text: t("No device connected – plug the iPhone in via USB and unlock it, or bring it into the same Wi-Fi.") });
    else if (st.device.developerMode === false && st.device.platform !== "tvos")
      out.push({ text: t("Developer Mode is off."), action: () => go("device"), label: t("Turn on") });
    if (info && st.device && info.platform !== st.device.platform)
      out.push({ text: info.platform === "tvos"
        ? t("This IPA is an Apple TV app – pick the Apple TV as the device.")
        : t("This IPA is for iPhone and iPad – an Apple TV needs the app's tvOS version.") });
    if (info?.encrypted) out.push({ text: t("This IPA is App Store encrypted (FairPlay) and cannot be re-signed.") });
    if (!bundleIdValid) out.push({ text: t("The bundle ID is not valid – letters, digits and hyphens, separated by dots.") });
    return out;
  });
  const quotaShort = $derived(!!plan?.error);

  function start() {
    if (!info) return;
    const name = displayName.trim();
    installIpa(info.path, name || info.name, {
      ...(name ? { displayName: name } : {}),
      ...(bundleId.trim() && !spare ? { bundleId: bundleId.trim() } : {}),
      ...(icon ? { icon } : {}),
      ...(keep ? { extensions: [...keep] } : {}),
      ...(spare ? { spareAppId: spare } : {}),
      ...(account ? { account } : {}),
    });
  }
</script>

<PageHeader title={t("Install app")} subtitle={t("Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.")} />

{#if !info && !inspecting}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="drop" class:dragging
       ondragover={(e) => { e.preventDefault(); dragging = true; }}
       ondragleave={() => (dragging = false)}
       ondrop={onDrop}>
    <div class="drop-icon"><Upload size={28} /></div>
    <h2>{t("Drag an IPA here")}</h2>
    <p class="muted">{t("or")}</p>
    <button class="btn primary" onclick={browse}><FolderOpen size={16} /> {t("Choose a file")}</button>
  </div>

  <h2 class="found-head">{t("Found in your folders")}</h2>
  {#if found === null}
    <div class="card list"><div class="skeleton" style="height:44px"></div></div>
  {:else if !found.length}
    <p class="muted">{t("No IPAs in Downloads, Documents or Desktop.")}</p>
  {:else}
    <div class="card list">
      {#each found as f (f.path)}
        <button class="row" onclick={() => choose(f.path)}>
          <FileArchive size={20} />
          <div class="grow">
            <div class="fname">{f.name}</div>
            <div class="faint small mono">{f.path}</div>
          </div>
          <span class="faint small">{mb(f.size)} · {relative(f.modified)}</span>
        </button>
      {/each}
    </div>
  {/if}
{:else if inspecting}
  <div class="card empty"><LoaderCircle size={28} class="spin" /><p>{t("Reading the IPA …")}</p></div>
{:else if info}
  <div class="card detail">
    <div class="detail-head">
      <button class="app-icon" class:custom={icon || info.icon} title={t("Change icon")}
              disabled={tvApp} onclick={() => iconInput?.click()}>
        {#if icon || info.icon}
          <img src={icon ?? info.icon} alt="" />
        {:else}
          <Box size={28} />
        {/if}
        <span class="icon-edit"><ImagePlus size={15} /></span>
      </button>
      <input type="file" accept="image/png,image/jpeg,image/webp" hidden bind:this={iconInput} onchange={pickIcon} />
      <div class="grow">
        <h2>{displayName.trim() || info.name}</h2>
        <p class="muted">{tvApp
          ? t("Version {version} · Apple TV · from tvOS {os}", { version: info.version || "?", os: info.minimumOs || "?" })
          : t("Version {version} · from iOS {ios}", { version: info.version || "?", ios: info.minimumOs || "?" })} · {mb(info.size)}</p>
        <p class="faint mono small selectable">{info.bundleId}</p>
      </div>
      <button class="btn icon ghost" title={t("Different IPA")} onclick={() => (info = null)}><X size={18} /></button>
    </div>

    <div class="stats">
      <div class="stat"><Puzzle size={17} /><b>{info.extensions.length}</b> {t("extensions")}</div>
      <div class="stat"><Layers size={17} /><b>{info.frameworks.length}</b> {t("frameworks")}</div>
      <div class="stat"><Sparkles size={17} /><b>{info.dylibs.length}</b> {t("injected dylibs")}</div>
    </div>

    <!-- Editor -->
    <section class="sect">
      <div class="sect-head">
        <h3><SlidersHorizontal size={16} /> {t("Customize")}</h3>
        <span class="faint tiny">{t("Optional – empty fields keep what the IPA says.")}</span>
      </div>

      {#if !tvApp}
      <div class="icon-row">
        <div class="icon-preview">
          {#if icon || info.icon}<img src={icon ?? info.icon} alt="" />{:else}<Box size={22} />{/if}
        </div>
        <div class="grow">
          <div class="row-title">{t("App icon")}</div>
          <div class="faint tiny">{iconError || (icon ? t("New icon – cropped to a square.") : t("Any image; it is cropped to a square."))}</div>
        </div>
        <button class="btn sm" onclick={() => iconInput?.click()}><ImagePlus size={15} /> {t("Choose image …")}</button>
        {#if icon}
          <button class="btn sm ghost" onclick={() => (icon = null)}><RotateCcw size={14} /> {t("Original icon")}</button>
        {/if}
      </div>
      {/if}

      <div class="fields">
        <div class="field">
          <label for="dn">{t("Name on the home screen")}</label>
          <input id="dn" type="text" bind:value={displayName} placeholder={info.name} maxlength="60" />
        </div>
        <div class="field">
          <label for="bid">{t("Bundle ID")}</label>
          <input id="bid" type="text" class="mono" bind:value={bundleId} disabled={!!spare}
                 class:invalid={!bundleIdValid}
                 placeholder={plan?.defaultBundleId ?? info.bundleId} spellcheck="false" />
          <span class="faint tiny">
            {spare
              ? t("The app runs under the unused App ID {id}.", { id: spare })
              : t("Must be unique at Apple. Empty: ModStaller picks one that fits your team.")}
          </span>
        </div>
      </div>
    </section>

    {#if info.extensionDetails.length}
      <section class="sect">
        <div class="sect-head">
          <h3><Puzzle size={16} /> {t("Extensions")}</h3>
          <span class="faint tiny">{t("Each kept extension needs an App ID of its own.")}</span>
        </div>
        {#each info.extensionDetails as ext (ext.path)}
          {@const on = keep?.includes(ext.path) ?? false}
          <label class="toggle" class:off={!ext.movable}>
            <input type="checkbox" checked={on} disabled={!ext.movable || keep === null}
                   onchange={(e) => toggle(ext, e.currentTarget.checked)} />
            <span class="switch"></span>
            <div class="grow">
              <div class="ext-name">{ext.name} <span class="chip">{kind(ext.point)}</span></div>
              <div class="faint mono tiny ellipsis">
                {ext.movable ? (plan?.extensions.find((x) => x.path === ext.path)?.identifier ?? ext.bundleId) : t("Cannot be kept – its ID does not belong to the app.")}
              </div>
            </div>
          </label>
        {/each}
      </section>
    {/if}
    {#if info.hasWatch}
      <p class="faint small note"><Watch size={14} /> {t("The Apple Watch app is removed – it cannot be installed this way.")}</p>
    {/if}

    <!-- Kosten und Kontingent -->
    {#if plan}
      <div class="cost">
        <QuotaMeter quota={plan.quota} isFree={plan.isFree} cost={plan.newAppIds.length} slots={plan.slots} />
        {#if !plan.newAppIds.length}
          <p class="faint small">{t("No new App ID needed – the ones this install uses already exist.")}</p>
        {/if}
        {#each plan.notes as n}<p class="faint small">{n}</p>{/each}
      </div>
    {:else if planning}
      <p class="faint small"><LoaderCircle size={13} class="spin" /> {t("Checking the App ID quota …")}</p>
    {/if}
    {#if planError}
      <div class="banner warn small"><TriangleAlert size={16} color="var(--warn)" /><div class="grow selectable">{planError}</div></div>
    {/if}

    {#if quotaShort && plan}
      <div class="banner bad fixes">
        <TriangleAlert size={18} color="var(--bad)" />
        <div class="grow">
          <div>{plan.error}</div>
          <div class="fix-buttons">
            {#if keep?.length}
              <button class="btn sm" onclick={() => (keep = [])}><Scissors size={14} /> {t("Leave out all extensions")}</button>
            {/if}
            {#if plan.spares.length}
              <select bind:value={spare} class="spare sm">
                <option value="">{t("Reuse an unused App ID …")}</option>
                {#each plan.spares as s (s.appIdId)}<option value={s.identifier}>{s.identifier}</option>{/each}
              </select>
            {/if}
          </div>
        </div>
      </div>
    {:else if spare}
      <div class="banner info small">
        <Recycle size={16} color="var(--accent)" />
        <div class="grow">{t("The app runs under the unused App ID {id}.", { id: spare })}</div>
        <button class="btn sm ghost" onclick={() => (spare = "")}>{t("Undo")}</button>
      </div>
    {/if}

    {#if slotsFull && plan?.slots}
      <div class="banner warn slots">
        <TriangleAlert size={18} color="var(--warn)" />
        <div class="grow">
          <div>{t("All {max} app slots of the free profile are taken – iOS will refuse a further app. Remove one first:", { max: plan.slots.max ?? 3 })}</div>
          <div class="slot-list">
            {#each plan.slots.apps as a (a.bundleId)}
              <div class="slot">
                <span class="grow">{a.name} <span class="faint mono tiny">{a.bundleId}</span></span>
                <button class="btn sm danger" disabled={busy()} onclick={() => uninstallApp(a)}><Trash2 size={14} /> {t("Remove")}</button>
              </div>
            {/each}
          </div>
        </div>
      </div>
    {/if}

    {#if accounts.length > 1}
      <div class="field account">
        <label for="acc">{t("Sign with")}</label>
        <select id="acc" bind:value={account}>
          <option value="">{t("Active account ({account})", { account: accounts.find((a) => a.active)?.label ?? "" })}</option>
          {#each accounts.filter((a) => !a.active) as a (a.adsid)}
            <option value={a.adsid}>{a.label}</option>
          {/each}
        </select>
      </div>
    {/if}

    {#each blockers as b}
      <div class="banner warn blocker">
        <TriangleAlert size={18} color="var(--warn)" />
        <div class="grow">{b.text}</div>
        {#if b.action}<button class="btn sm" onclick={b.action}>{b.label}</button>{/if}
      </div>
    {/each}

    <div class="actions">
      <button class="btn ghost" onclick={() => (info = null)}>{t("Back")}</button>
      {#if displayName || bundleId || icon || spare}
        <button class="btn ghost" onclick={() => { const k = keep; resetEditor(); keep = k; }}><RotateCcw size={15} /> {t("Undo changes")}</button>
      {/if}
      <button class="btn primary" disabled={busy() || blockers.length > 0 || quotaShort} onclick={start}>
        {t("Sign & install")}
      </button>
    </div>
  </div>
{/if}

{#if inspectError}
  <div class="banner bad err">
    <TriangleAlert size={18} color="var(--bad)" />
    <div class="grow selectable">{inspectError}</div>
    <button class="btn sm" onclick={() => (inspectError = "")}>OK</button>
  </div>
{/if}

<style>
  .drop {
    display: grid; justify-items: center; gap: 8px;
    padding: 44px 24px; border-radius: 18px;
    border: 2px dashed var(--border-strong);
    background: var(--bg-elev);
    transition: border-color 0.15s, background 0.15s, transform 0.15s;
  }
  .drop.dragging { border-color: var(--accent); background: var(--accent-soft); transform: scale(1.01); }
  .drop-icon { width: 60px; height: 60px; border-radius: 18px; display: grid; place-items: center; margin-bottom: 6px;
               background: var(--accent-grad); color: #fff; box-shadow: 0 8px 24px rgb(110 100 255 / 0.35); }
  .drop p { font-size: 13px; }

  .found-head { margin: 30px 0 12px; }
  .list { padding: 6px; display: grid; }
  .row { display: flex; align-items: center; gap: 14px; padding: 11px 12px; border: none; border-radius: 10px;
         background: transparent; color: var(--text-2); font: inherit; text-align: left; cursor: pointer; }
  .row:hover { background: var(--surface-2); }
  .row:hover :global(svg) { color: var(--accent); }
  .fname { color: var(--text); font-weight: 550; }
  .grow { flex: 1; min-width: 0; }
  .small { font-size: 12px; }
  .mono.small { font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .detail { padding: 24px; display: grid; gap: 18px; }
  .detail-head { display: flex; gap: 16px; align-items: flex-start; }
  .detail-head p { margin-top: 3px; }
  .app-icon { width: 60px; height: 60px; border-radius: 16px; flex: none; display: grid; place-items: center;
              background: var(--accent-grad); color: #fff; border: 0; padding: 0; cursor: pointer;
              position: relative; overflow: hidden; }
  .app-icon.custom { background: var(--surface-2); }
  .app-icon img { width: 100%; height: 100%; object-fit: cover; }
  .icon-edit { position: absolute; inset: auto 0 0 0; height: 22px; display: grid; place-items: center;
               background: rgb(0 0 0 / 0.45); color: #fff; opacity: 0; transition: opacity 0.15s; }
  .app-icon:hover .icon-edit, .app-icon:focus-visible .icon-edit { opacity: 1; }

  input.invalid { border-color: var(--bad); }
  input.invalid:focus { box-shadow: 0 0 0 3px var(--bad-soft); }
  .tiny { font-size: 11.5px; }
  .ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .note { display: flex; gap: 6px; align-items: center; margin: 0; }

  /* Abschnitte wie auf der Einstellungsseite: Ueberschrift mit Icon, darunter
     ruhige Flaechen statt nackter Formularelemente. */
  .sect { display: grid; gap: 10px; }
  .sect-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .sect-head h3 { display: flex; align-items: center; gap: 8px; font-size: 14.5px; }
  .sect-head h3 :global(svg) { color: var(--accent); align-self: center; }
  .icon-row { display: flex; align-items: center; gap: 12px; padding: 12px 14px;
              border-radius: 12px; border: 1px solid var(--border); flex-wrap: wrap; }
  .icon-preview { width: 44px; height: 44px; border-radius: 11px; overflow: hidden; flex: none;
                  display: grid; place-items: center; background: var(--surface-2); color: var(--text-3); }
  .icon-preview img { width: 100%; height: 100%; object-fit: cover; }
  .row-title { font-weight: 550; }
  .fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px 16px; }
  .fields .field { align-content: start; }
  .fields .tiny { margin-top: 1px; }

  /* Derselbe Schalter wie in Settings.svelte. */
  .toggle { display: flex; gap: 14px; align-items: center; cursor: pointer; padding: 12px 14px;
            border-radius: 12px; border: 1px solid var(--border); }
  .toggle.off { cursor: default; opacity: 0.55; }
  .toggle input { display: none; }
  .switch { width: 38px; height: 22px; flex: none; border-radius: 99px; background: var(--border-strong);
            position: relative; transition: background 0.15s; }
  .switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px;
                   border-radius: 50%; background: #fff; transition: transform 0.15s; }
  .toggle input:checked + .switch { background: var(--accent); }
  .toggle input:checked + .switch::after { transform: translateX(16px); }
  .ext-name { font-weight: 550; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

  .cost { display: grid; gap: 6px; }
  .cost p { margin: 0; }
  .fixes, .slots { font-size: 13px; }
  .fix-buttons { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
  .spare { max-width: 100%; width: auto; }
  select.sm { height: 30px; padding: 0 10px; font-size: 13px; border-radius: 8px; }
  .slot-list { display: grid; gap: 6px; margin-top: 10px; }
  .slot { display: flex; align-items: center; gap: 10px; }
  .stats { display: flex; gap: 10px; flex-wrap: wrap; }
  .stat { display: flex; align-items: center; gap: 8px; padding: 9px 14px; border-radius: 10px; background: var(--surface-2); color: var(--text-2); font-size: 13px; }
  .stat b { color: var(--text); }


  .blocker { font-size: 13px; }
  .actions { display: flex; justify-content: flex-end; gap: 8px; }
  .err { margin-top: 16px; font-size: 13px; white-space: pre-wrap; }
</style>
