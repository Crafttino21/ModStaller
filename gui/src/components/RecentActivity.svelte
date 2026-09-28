<script lang="ts">
  // Die letzten Ereignisse in der Uebersicht - der Rest steht im Protokoll.
  import { Activity, ChevronRight, CircleCheck, CircleX, TriangleAlert, Info } from "@lucide/svelte";
  import { go, ui } from "../lib/state.svelte";
  import { locale, t } from "../lib/i18n.svelte";

  // Pro Vorgang genau eine Zeile: das Ergebnis - oder, solange er laeuft,
  // der aktuelle Schritt. Rueckwaerts gelesen ist das jeweils der neueste
  // Eintrag des Vorgangs. Ereignisse ohne Vorgang (iPhone verbunden, ...)
  // stehen fuer sich.
  const recent = $derived.by(() => {
    const seenJobs = new Set<unknown>();
    const out = [];
    for (const e of [...ui.log.entries].reverse()) {
      if (e.level === "debug") continue;
      if (e.job != null) {
        if (seenJobs.has(e.job)) continue;
        seenJobs.add(e.job);
      }
      out.push(e);
      if (out.length === 5) break;
    }
    return out;
  });

  const ago = (ts: number) => {
    const s = Date.now() / 1000 - ts;
    if (s < 60) return t("just now");
    if (s < 3600) return t("{minutes} min ago", { minutes: Math.floor(s / 60) });
    return new Date(ts * 1000).toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" });
  };
</script>

{#if recent.length}
  <div class="head">
    <h2>{t("Recent activity")}</h2>
    <button class="btn sm ghost" onclick={() => go("log")}>{t("Log")} <ChevronRight size={15} /></button>
  </div>
  <div class="card list">
    {#each recent as e (e.id)}
      <div class="row {e.level}">
        <span class="ic">
          {#if e.level === "success"}<CircleCheck size={16} />
          {:else if e.level === "error"}<CircleX size={16} />
          {:else if e.level === "warn"}<TriangleAlert size={16} />
          {:else}<Info size={16} />{/if}
        </span>
        <span class="msg" title={e.message}>{e.message.split("\n")[0]}</span>
        <span class="when">{ago(e.ts)}</span>
      </div>
    {/each}
  </div>
{:else}
  <div class="head"><h2>{t("Recent activity")}</h2></div>
  <div class="card list quiet"><Activity size={16} /> {t("Nothing has happened yet.")}</div>
{/if}

<style>
  .head { display: flex; align-items: center; justify-content: space-between; margin: 30px 0 12px; }
  .list { padding: 6px 16px; }
  .row { display: flex; align-items: center; gap: 12px; padding: 9px 0; font-size: 13px; }
  .row + .row { border-top: 1px solid var(--border); }
  .ic { display: flex; color: var(--text-3); flex: none; }
  .success .ic { color: var(--ok); }
  .warn .ic { color: var(--warn); }
  .error .ic { color: var(--bad); }
  .msg { flex: 1; min-width: 0; color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .success .msg { color: var(--text); }
  .when { flex: none; font-size: 12px; color: var(--text-3); font-variant-numeric: tabular-nums; }
  .quiet { display: flex; align-items: center; gap: 8px; padding: 14px 16px; color: var(--text-3); font-size: 13px; }
</style>
