<script lang="ts">
  // Wie viel noch offen ist: App-IDs diese Woche und App-Slots auf dem iPhone.
  // Die Zahlen kommen von Apple selbst (modstaller/quota.py) - nur *wann* die
  // naechste wieder frei wird, ist geschaetzt.
  import { KeyRound, Smartphone } from "@lucide/svelte";
  import { date } from "../lib/format";
  import { t } from "../lib/i18n.svelte";
  import type { Quota, Slots } from "../lib/types";

  let { quota, isFree, cost = 0, slots = null }: {
    quota: Quota;
    isFree: boolean;
    /** Was die geplante Installation kosten wuerde - wird hervorgehoben. */
    cost?: number;
    slots?: Slots | null;
  } = $props();

  const max = $derived(quota.maximum ?? 10);
  const available = $derived(quota.available ?? max);
  const used = $derived(Math.max(0, max - available));
  const over = $derived(cost > available);
  /** Segmente: belegt, von dieser Installation, frei. */
  const segments = $derived(Array.from({ length: max }, (_, i) =>
    i < used ? "used" : i < used + cost ? (over ? "over" : "cost") : "free"));
  const upcoming = $derived(quota.returnsAt.filter((ts) => ts * 1000 > Date.now()).slice(0, 3));
</script>

{#if isFree}
  <div class="meter">
    <div class="head">
      <span class="label"><KeyRound size={14} /> {t("App IDs this week")}</span>
      <span class="value" class:bad={available === 0 || over}>
        {t("{available} of {max} left", { available, max })}
      </span>
    </div>
    <div class="bar" style="--n: {max}">
      {#each segments as s}<span class={s}></span>{/each}
    </div>
    {#if cost}
      <p class="small" class:bad={over}>
        {over
          ? t("This install needs {cost} – {missing} more than are left.", { cost, missing: cost - available })
          : t("This install uses {cost} of them.", { cost })}
      </p>
    {/if}
    {#if quota.nextFreeAt}
      <p class="faint small">{t("The next one frees up around {date}.", { date: date(quota.nextFreeAt) })}</p>
    {:else if upcoming.length && available < max}
      <p class="faint small">{t("Free again: {dates}", { dates: upcoming.map(date).join(" · ") })}</p>
    {/if}
    <p class="faint tiny">{t("Apple counts App IDs created in the last 7 days – deleting one does not give it back.")}</p>
  </div>

  {#if slots && slots.max}
    <div class="meter">
      <div class="head">
        <span class="label"><Smartphone size={14} /> {t("Apps on the iPhone (free profile)")}</span>
        <span class="value" class:bad={slots.used >= slots.max}>{t("{used} of {max} used", { used: slots.used, max: slots.max })}</span>
      </div>
      <div class="bar" style="--n: {slots.max}">
        {#each Array.from({ length: slots.max }, (_, i) => i < slots.used) as full}<span class={full ? "used" : "free"}></span>{/each}
      </div>
    </div>
  {/if}
{:else}
  <p class="faint small">{t("Paid account – no weekly limit on App IDs and no limit on apps.")}</p>
{/if}

<style>
  .meter { display: grid; gap: 7px; padding: 12px 14px; border-radius: 12px; background: var(--surface-2); }
  .meter + .meter { margin-top: 8px; }
  .head { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
  .label { display: flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 550; color: var(--text-2); }
  .value { font-size: 13px; font-weight: 650; font-variant-numeric: tabular-nums; }
  .bar { display: grid; grid-template-columns: repeat(var(--n), 1fr); gap: 3px; }
  .bar span { height: 8px; border-radius: 3px; background: var(--border); }
  .bar .used { background: var(--text-3); }
  .bar .cost { background: var(--accent); }
  .bar .over { background: var(--bad); }
  .small { margin: 0; font-size: 12.5px; }
  .tiny { margin: 0; font-size: 11.5px; }
  .bad { color: var(--bad); }
</style>
