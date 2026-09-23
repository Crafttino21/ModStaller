<script lang="ts">
  import {
    Upload, FileArchive, FolderOpen, TriangleAlert, Puzzle, Layers, Box, X, LoaderCircle, Sparkles,
  } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { busy, errorText, go, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { mb, relative } from "../lib/format";
  import { installIpa } from "../lib/actions";
  import type { FoundIpa, IpaInfo } from "../lib/types";

  let found = $state<FoundIpa[] | null>(null);
  let info = $state<IpaInfo | null>(null);
  let inspecting = $state(false);
  let inspectError = $state("");
  let keepExtensions = $state(false);
  let dragging = $state(false);

  call<FoundIpa[]>("ipa.find").then((f) => (found = f.sort((a, b) => b.modified - a.modified)), () => (found = []));

  async function choose(path: string) {
    info = null;
    inspectError = "";
    keepExtensions = false;
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

  const st = $derived(ui.status);
  const blockers = $derived.by(() => {
    const out: { text: string; action?: () => void; label?: string }[] = [];
    if (!st) return out;
    if (!st.loggedIn) out.push({ text: "Nicht bei Apple angemeldet.", action: () => go("account"), label: "Anmelden" });
    if (!st.device) out.push({ text: st.deviceAttached ? "iPhone ist angesteckt, aber gesperrt oder nicht gepairt." : "Kein iPhone verbunden – per USB anstecken und entsperren." });
    else if (!st.device.developerMode)
      out.push({ text: "Entwicklermodus ist aus: Einstellungen › Datenschutz & Sicherheit › Entwicklermodus." });
    if (info?.encrypted) out.push({ text: "Diese IPA ist App-Store-verschlüsselt (FairPlay) und lässt sich nicht neu signieren." });
    return out;
  });

  function start() {
    if (info) installIpa(info.path, info.name, keepExtensions);
  }
</script>

<PageHeader title="App installieren" subtitle="IPA wählen – ModStaller signiert sie mit deinem Apple-Konto und spielt sie aufs iPhone." />

{#if !info && !inspecting}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="drop" class:dragging
       ondragover={(e) => { e.preventDefault(); dragging = true; }}
       ondragleave={() => (dragging = false)}
       ondrop={onDrop}>
    <div class="drop-icon"><Upload size={28} /></div>
    <h2>IPA hierher ziehen</h2>
    <p class="muted">oder</p>
    <button class="btn primary" onclick={browse}><FolderOpen size={16} /> Datei auswählen</button>
  </div>

  <h2 class="found-head">In deinen Ordnern gefunden</h2>
  {#if found === null}
    <div class="card list"><div class="skeleton" style="height:44px"></div></div>
  {:else if !found.length}
    <p class="muted">Keine IPAs in Downloads, Dokumente, Desktop oder Schreibtisch.</p>
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
  <div class="card empty"><LoaderCircle size={28} class="spin" /><p>IPA wird gelesen …</p></div>
{:else if info}
  <div class="card detail">
    <div class="detail-head">
      <div class="app-icon"><Box size={28} /></div>
      <div class="grow">
        <h2>{info.name}</h2>
        <p class="muted">Version {info.version || "?"} · ab iOS {info.minimumOs || "?"} · {mb(info.size)}</p>
        <p class="faint mono small selectable">{info.bundleId}</p>
      </div>
      <button class="btn icon ghost" title="Andere IPA" onclick={() => (info = null)}><X size={18} /></button>
    </div>

    <div class="stats">
      <div class="stat"><Puzzle size={17} /><b>{info.extensions.length}</b> Extensions</div>
      <div class="stat"><Layers size={17} /><b>{info.frameworks.length}</b> Frameworks</div>
      <div class="stat"><Sparkles size={17} /><b>{info.dylibs.length}</b> injizierte dylibs</div>
    </div>

    {#if info.extensions.length}
      <label class="toggle">
        <input type="checkbox" bind:checked={keepExtensions} />
        <span class="switch"></span>
        <div>
          <div>Extensions behalten</div>
          <div class="faint small">
            Kostet {info.extensions.length} App-ID(s) vom Wochenkontingent (10 pro Woche bei Gratis-Accounts).
            Die App selbst läuft auch ohne.
          </div>
        </div>
      </label>
    {/if}

    {#each blockers as b}
      <div class="banner warn blocker">
        <TriangleAlert size={18} color="var(--warn)" />
        <div class="grow">{b.text}</div>
        {#if b.action}<button class="btn sm" onclick={b.action}>{b.label}</button>{/if}
      </div>
    {/each}

    <div class="actions">
      <button class="btn ghost" onclick={() => (info = null)}>Zurück</button>
      <button class="btn primary" disabled={busy() || blockers.length > 0} onclick={start}>
        Signieren &amp; installieren
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
              background: var(--accent-grad); color: #fff; }
  .stats { display: flex; gap: 10px; flex-wrap: wrap; }
  .stat { display: flex; align-items: center; gap: 8px; padding: 9px 14px; border-radius: 10px; background: var(--surface-2); color: var(--text-2); font-size: 13px; }
  .stat b { color: var(--text); }

  .toggle { display: flex; gap: 14px; align-items: flex-start; cursor: pointer; padding: 14px; border-radius: 12px; border: 1px solid var(--border); }
  .toggle input { display: none; }
  .switch { width: 38px; height: 22px; flex: none; border-radius: 99px; background: var(--border-strong); position: relative; transition: background 0.15s; margin-top: 1px; }
  .switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform 0.15s; }
  .toggle input:checked + .switch { background: var(--accent); }
  .toggle input:checked + .switch::after { transform: translateX(16px); }

  .blocker { font-size: 13px; }
  .actions { display: flex; justify-content: flex-end; gap: 8px; }
  .err { margin-top: 16px; font-size: 13px; white-space: pre-wrap; }
</style>
