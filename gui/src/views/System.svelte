<script lang="ts">
  import { CircleCheck, CircleX, CircleDashed, RefreshCw, LoaderCircle } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { errorText } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import type { Check } from "../lib/types";

  let checks = $state<Check[] | null>(null);
  let running = $state(false);
  let error = $state("");
  let version = $state("");

  async function run() {
    running = true;
    error = "";
    try {
      checks = await call<Check[]>("doctor");
    } catch (err) {
      error = errorText(err);
    } finally {
      running = false;
    }
  }
  run();
  call<string>("version").then((v) => (version = v), () => {});

  const problems = $derived(checks?.filter((c) => !c.ok && c.kind === "problem").length ?? 0);
  const todos = $derived(checks?.filter((c) => !c.ok && c.kind === "todo").length ?? 0);
</script>

<PageHeader title="Systemcheck" subtitle="Ist alles da, was ModStaller braucht?">
  {#snippet actions()}
    <button class="btn" onclick={run} disabled={running}>
      {#if running}<LoaderCircle size={16} class="spin" />{:else}<RefreshCw size={16} />{/if} Erneut prüfen
    </button>
  {/snippet}
</PageHeader>

{#if checks}
  <div class="summary banner {problems ? 'bad' : todos ? 'warn' : 'info'}">
    {#if problems}{problems} Punkt(e) zu klären.{:else if todos}System ist bereit – noch {todos} Schritt(e) offen.{:else}Alles bereit.{/if}
  </div>
{/if}
{#if error}<div class="banner bad selectable">{error}</div>{/if}

<div class="card list">
  {#if !checks}
    {#each [1, 2, 3, 4, 5] as _}<div class="row"><div class="skeleton" style="height:20px;width:100%"></div></div>{/each}
  {:else}
    {#each checks as c (c.label)}
      <div class="row">
        <span class="ic {c.ok ? 'ok' : c.kind === 'todo' ? 'todo' : 'bad'}">
          {#if c.ok}<CircleCheck size={19} />{:else if c.kind === "todo"}<CircleDashed size={19} />{:else}<CircleX size={19} />{/if}
        </span>
        <div class="grow">
          <div class="label">{c.label}</div>
          {#if c.detail}<div class="faint mono tiny selectable">{c.detail}</div>{/if}
          {#if !c.ok && c.hint}<div class="hint selectable">{c.hint}</div>{/if}
        </div>
      </div>
    {/each}
  {/if}
</div>

<p class="faint foot">ModStaller {version} · Daten unter <code>~/.local/share/modstaller</code> (Secrets mit 0600).</p>

<style>
  .summary { margin-bottom: 14px; font-weight: 550; }
  .list { padding: 6px 18px; }
  .row { display: flex; gap: 14px; align-items: flex-start; padding: 14px 0; }
  .row + .row { border-top: 1px solid var(--border); }
  .ic { margin-top: 1px; }
  .ic.ok { color: var(--ok); }
  .ic.bad { color: var(--bad); }
  .ic.todo { color: var(--warn); }
  .grow { flex: 1; min-width: 0; }
  .label { font-weight: 550; }
  .tiny { font-size: 11.5px; overflow-wrap: anywhere; }
  .hint { margin-top: 4px; font-size: 13px; color: var(--text-2); }
  .foot { margin-top: 16px; font-size: 12px; }
</style>
