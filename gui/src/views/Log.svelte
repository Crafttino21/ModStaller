<script lang="ts">
  // Live-Protokoll: alles, was ModStaller tut - Installationen, JIT,
  // Geraete-Ereignisse, Anmeldung. Neuestes unten, wie in einem Terminal.
  import {
    CircleCheck, CircleX, TriangleAlert, Info, Pause, Play, Copy, FolderOpen, Search, ArrowDown,
  } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { toast, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import type { LogEntry } from "../lib/types";

  const SOURCES: Record<LogEntry["source"], string> = {
    install: "Installieren", refresh: "Erneuern", jit: "JIT", apps: "Apps",
    device: "Gerät", account: "Konto", system: "System",
  };
  const LEVELS = [
    { id: "all", label: "Alles" },
    { id: "warn", label: "Warnungen" },
    { id: "error", label: "Fehler" },
  ] as const;
  const RANK = { debug: 0, info: 1, success: 1, warn: 2, error: 3 };

  let level = $state<"all" | "warn" | "error">("all");
  let source = $state<LogEntry["source"] | "all">("all");
  let query = $state("");
  let live = $state(true);
  let listEl = $state<HTMLDivElement>();
  let atBottom = $state(true);
  let missed = $state(0);
  let lastCount = 0;

  const shown = $derived(
    ui.log.entries.filter((e) =>
      (level === "all" || RANK[e.level] >= RANK[level]) &&
      (source === "all" || e.source === source) &&
      (!query || e.message.toLowerCase().includes(query.toLowerCase()))),
  );

  // Folgen, solange "Live" an ist und man unten steht - sonst mitzaehlen.
  $effect(() => {
    const n = shown.length;
    const added = n - lastCount;
    lastCount = n;
    if (!listEl) return;
    if (live && atBottom) {
      queueMicrotask(() => listEl && (listEl.scrollTop = listEl.scrollHeight));
    } else if (added > 0) {
      missed += added;
    }
  });

  function onScroll() {
    if (!listEl) return;
    atBottom = listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight < 40;
    if (atBottom) missed = 0;
  }

  function jumpDown() {
    live = true;
    missed = 0;
    listEl?.scrollTo({ top: listEl.scrollHeight, behavior: "smooth" });
  }

  const time = (ts: number) =>
    new Date(ts * 1000).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const day = (ts: number) => new Date(ts * 1000).toLocaleDateString("de-DE");

  function asText(entries: LogEntry[]) {
    return entries
      .map((e) => `${day(e.ts)} ${time(e.ts)} ${e.level.toUpperCase().padEnd(7)} [${SOURCES[e.source] ?? e.source}] ${e.message}`)
      .join("\n");
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(asText(shown));
      toast(`${shown.length} Einträge kopiert.`);
    } catch {
      toast("Kopieren nicht möglich.", "warn");
    }
  }

  async function showFile() {
    try {
      await window.backend.showFile(await call<string>("log.path"));
    } catch {
      toast("Log-Datei nicht gefunden.", "warn");
    }
  }
</script>

<PageHeader title="Protokoll" subtitle="Was ModStaller tut – live. Die komplette Historie steht in der Log-Datei.">
  {#snippet actions()}
    <button class="btn" onclick={() => (live ? (live = false) : jumpDown())} title={live ? "Anhalten" : "Weiter live folgen"}>
      {#if live}<Pause size={15} /> Live{:else}<Play size={15} /> Angehalten{/if}
    </button>
    <button class="btn" onclick={copy} disabled={!shown.length}><Copy size={15} /> Kopieren</button>
    <button class="btn" onclick={showFile}><FolderOpen size={15} /> Log-Datei</button>
  {/snippet}
</PageHeader>

<div class="filters">
  <div class="seg">
    {#each LEVELS as l}
      <button class:on={level === l.id} onclick={() => (level = l.id)}>{l.label}</button>
    {/each}
  </div>
  <div class="seg">
    <button class:on={source === "all"} onclick={() => (source = "all")}>Alle Bereiche</button>
    {#each Object.entries(SOURCES) as [id, label]}
      <button class:on={source === id} onclick={() => (source = id as LogEntry["source"])}>{label}</button>
    {/each}
  </div>
  <div class="search"><Search size={15} /><input type="search" placeholder="Suchen" bind:value={query} /></div>
</div>

<div class="card log-wrap">
  <div class="log selectable" bind:this={listEl} onscroll={onScroll}>
    {#each shown as e (e.id)}
      <div class="row {e.level}">
        <span class="t">{time(e.ts)}</span>
        <span class="lv">
          {#if e.level === "success"}<CircleCheck size={14} />
          {:else if e.level === "error"}<CircleX size={14} />
          {:else if e.level === "warn"}<TriangleAlert size={14} />
          {:else}<Info size={14} />{/if}
        </span>
        <span class="src {e.source}">{SOURCES[e.source] ?? e.source}</span>
        <span class="msg">{e.message}</span>
      </div>
    {:else}
      <div class="empty-log">
        {ui.log.entries.length ? "Keine Einträge für diesen Filter." : "Noch nichts passiert. Sobald du ein iPhone ansteckst oder etwas installierst, erscheint es hier."}
      </div>
    {/each}
  </div>
  {#if missed > 0}
    <button class="missed" onclick={jumpDown}><ArrowDown size={14} /> {missed} neue</button>
  {/if}
</div>

<style>
  .filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 12px; }
  .seg { display: flex; flex-wrap: wrap; gap: 2px; padding: 3px; border-radius: 10px; background: var(--surface); border: 1px solid var(--border); }
  .seg button { border: none; background: transparent; color: var(--text-2); font: inherit; font-size: 12.5px; font-weight: 550;
                padding: 5px 10px; border-radius: 7px; cursor: pointer; }
  .seg button:hover { color: var(--text); }
  .seg button.on { background: var(--accent-soft); color: var(--text); }
  .search { display: flex; align-items: center; gap: 6px; color: var(--text-3); margin-left: auto; }
  .search input { height: 34px; width: 200px; }

  .log-wrap { position: relative; overflow: hidden; }
  .log { height: calc(100vh - 290px); min-height: 260px; overflow: auto; padding: 8px 0;
         font-family: var(--mono); font-size: 12.5px; line-height: 1.55; }
  .row { display: grid; grid-template-columns: 70px 20px 96px 1fr; gap: 8px; align-items: baseline; padding: 3px 16px; }
  .row:hover { background: var(--surface-2); }
  .t { color: var(--text-3); font-variant-numeric: tabular-nums; }
  .lv { display: flex; align-self: center; color: var(--text-3); }
  .row.success .lv { color: var(--ok); }
  .row.warn .lv { color: var(--warn); }
  .row.error .lv { color: var(--bad); }
  .row.error .msg { color: var(--bad); }
  .row.warn .msg { color: var(--warn); }
  .row.success .msg { color: var(--text); font-weight: 600; }
  .msg { color: var(--text-2); white-space: pre-wrap; overflow-wrap: anywhere; }

  .src { font-family: "Inter Variable", system-ui, sans-serif; font-size: 11px; font-weight: 600; text-align: center;
         padding: 1px 6px; border-radius: 6px; background: var(--surface-2); color: var(--text-2); white-space: nowrap; }
  .src.install, .src.refresh { background: var(--accent-soft); color: var(--accent); }
  .src.jit { background: rgb(62 201 240 / 0.14); color: var(--accent-2); }
  .src.device { background: var(--ok-soft); color: var(--ok); }
  .src.account { background: var(--warn-soft); color: var(--warn); }

  .empty-log { padding: 40px 20px; text-align: center; color: var(--text-3); font-family: "Inter Variable", system-ui, sans-serif; font-size: 13.5px; }
  .missed { position: absolute; left: 50%; bottom: 14px; transform: translateX(-50%);
            display: flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 99px; border: none;
            background: var(--accent-grad); color: #fff; font: inherit; font-size: 12.5px; font-weight: 600; cursor: pointer;
            box-shadow: 0 6px 20px rgb(110 100 255 / 0.35); }
</style>
