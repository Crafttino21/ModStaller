<script lang="ts">
  let { level, charging }: { level: number; charging: boolean } = $props();

  const color = $derived(
    charging ? "var(--ok)" : level <= 20 ? "var(--bad)" : level <= 35 ? "var(--warn)" : "var(--text-2)",
  );
</script>

<span class="battery" title={charging ? `Lädt – ${level} %` : `Akku ${level} %`}>
  <svg viewBox="0 0 26 12" aria-hidden="true">
    <rect x="0.75" y="0.75" width="21.5" height="10.5" rx="3" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5" />
    <rect x="23.2" y="3.8" width="1.8" height="4.4" rx="0.9" fill="currentColor" opacity="0.5" />
    <rect x="2.5" y="2.5" width={Math.max(1.5, (18 * Math.min(100, level)) / 100)} height="7" rx="1.6" fill={color} />
    {#if charging}
      <path d="M12.6 1.8 8.8 6.6h2.8l-1 3.6 3.9-4.9h-2.8z" fill="#fff" stroke="#0b0c10" stroke-width="0.5" />
    {/if}
  </svg>
  <span style:color={color}>{level} %</span>
</span>

<style>
  .battery { display: inline-flex; align-items: center; gap: 5px; color: var(--text-2); font-size: 12px;
             font-variant-numeric: tabular-nums; font-weight: 550; }
  svg { width: 24px; height: 12px; }
</style>
