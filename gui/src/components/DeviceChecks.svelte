<script lang="ts">
  // iPhone-Check: laeuft beim Anstecken von selbst (state.svelte.ts) und
  // bietet fuer jeden Punkt, der sich automatisch beheben laesst, einen Knopf.
  import {
    CircleCheck, CircleX, TriangleAlert, Info, CircleMinus, RefreshCw, LoaderCircle, Wrench, ShieldCheck,
  } from "@lucide/svelte";
  import { busy, refreshChecks, ui } from "../lib/state.svelte";
  import { fixCheck } from "../lib/actions";
  import { t } from "../lib/i18n.svelte";

  let { compact = false }: { compact?: boolean } = $props();

  const list = $derived(ui.checks.list ?? []);
  const bad = $derived(list.filter((c) => c.state === "bad").length);
  const warn = $derived(list.filter((c) => c.state === "warn").length);
  // Kompakt: nur, was Aufmerksamkeit braucht oder sich beheben laesst.
  const shown = $derived(compact ? list.filter((c) => c.state === "bad" || c.state === "warn" || c.fix) : list);
</script>

<div class="card box">
  <div class="head">
    <div class="icon" class:ok={list.length && !bad && !warn} class:bad={bad}><ShieldCheck size={20} /></div>
    <div class="grow">
      <h2>iPhone-Check</h2>
      <p class="muted small">
        {#if ui.checks.loading && !list.length}
          {t("Checking …")}
        {:else if !list.length}
          {ui.checks.error || t("Not checked yet.")}
        {:else if bad}
          {t("{count} point(s) prevent sideloading.", { count: bad })}
        {:else if warn}
          Bereit – {warn} Hinweis(e).
        {:else}
          {t("Everything ready for sideloading.")}
        {/if}
      </p>
    </div>
    <button class="btn sm ghost" title={t("Check again")} disabled={ui.checks.loading || busy()} onclick={refreshChecks}>
      {#if ui.checks.loading}<LoaderCircle size={15} class="spin" />{:else}<RefreshCw size={15} />{/if}
      {compact ? "" : t("Check again")}
    </button>
  </div>

  {#if ui.checks.loading && !list.length}
    <div class="skeleton" style="height:44px;margin-top:14px"></div>
  {/if}

  {#if shown.length}
    <div class="rows">
      {#each shown as c (c.id)}
        <div class="row">
          <span class="st {c.state}">
            {#if c.state === "ok"}<CircleCheck size={18} />
            {:else if c.state === "bad"}<CircleX size={18} />
            {:else if c.state === "warn"}<TriangleAlert size={18} />
            {:else if c.state === "na"}<CircleMinus size={18} />
            {:else}<Info size={18} />{/if}
          </span>
          <div class="grow">
            <div class="label">{c.label}</div>
            {#if c.detail}<div class="detail">{c.detail}</div>{/if}
            {#if c.manual && c.state !== "ok"}<div class="manual">{c.manual}</div>{/if}
          </div>
          {#if c.fix}
            <button class="btn sm {c.state === 'bad' ? 'primary' : ''}" disabled={busy() || ui.checks.loading}
                    onclick={() => fixCheck(c)}>
              <Wrench size={14} /> {c.fix_label}
            </button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .box { padding: 18px 20px; }
  .head { display: flex; align-items: center; gap: 14px; }
  .icon { width: 40px; height: 40px; border-radius: 12px; flex: none; display: grid; place-items: center;
          background: var(--surface-2); color: var(--text-3); }
  .icon.ok { background: var(--ok-soft); color: var(--ok); }
  .icon.bad { background: var(--bad-soft); color: var(--bad); }
  .grow { flex: 1; min-width: 0; }
  .small { font-size: 13px; margin-top: 2px; }
  .rows { margin-top: 12px; }
  .row { display: flex; gap: 12px; align-items: flex-start; padding: 11px 0; border-top: 1px solid var(--border); }
  .row .btn { flex: none; margin-top: 2px; }
  .st { margin-top: 1px; flex: none; }
  .st.ok { color: var(--ok); }
  .st.bad { color: var(--bad); }
  .st.warn { color: var(--warn); }
  .st.info { color: var(--accent); }
  .st.na { color: var(--text-3); }
  .label { font-weight: 550; }
  .detail { font-size: 13px; color: var(--text-2); }
  .manual { font-size: 12.5px; color: var(--text-2); margin-top: 4px; padding: 7px 10px; border-radius: 8px; background: var(--surface-2); }
</style>
