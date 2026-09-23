<script lang="ts">
  // Restlaufzeit als Ring: voll = frisch signiert, leer = abgelaufen.
  let { daysLeft, total = 7, urgentDays = 2, size = 54 }:
    { daysLeft: number; total?: number; urgentDays?: number; size?: number } = $props();

  const r = 22;
  const c = 2 * Math.PI * r;
  const frac = $derived(Math.min(1, Math.max(0, daysLeft / Math.max(total, 1))));
  const color = $derived(
    daysLeft < 0 ? "var(--bad)" : daysLeft <= urgentDays ? "var(--warn)" : "var(--ok)",
  );
  const label = $derived(
    daysLeft < 0 ? "–" : daysLeft < 1 ? `${Math.max(1, Math.round(daysLeft * 24))}h` : `${Math.floor(daysLeft)}d`,
  );
</script>

<div class="ring" style:width="{size}px" style:height="{size}px">
  <svg viewBox="0 0 54 54">
    <circle cx="27" cy="27" {r} class="track" />
    <circle cx="27" cy="27" {r} class="value" stroke={color}
            stroke-dasharray={c} stroke-dashoffset={c * (1 - frac)} />
  </svg>
  <span style:color={color}>{label}</span>
</div>

<style>
  .ring { position: relative; flex: none; }
  svg { width: 100%; height: 100%; transform: rotate(-90deg); }
  circle { fill: none; stroke-width: 5; }
  .track { stroke: var(--surface-2); }
  .value { stroke-linecap: round; transition: stroke-dashoffset 0.6s ease; }
  span {
    position: absolute; inset: 0; display: grid; place-items: center;
    font-size: 12.5px; font-weight: 700; font-variant-numeric: tabular-nums;
  }
</style>
