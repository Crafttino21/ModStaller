<script lang="ts">
  // Gezeichnetes Geraet in der Bauform des echten: Home-Button, Notch oder
  // Dynamic Island. Bewusst kein Produktfoto - nur die Silhouette.
  let { form = "island", height = 64 }: { form?: string; height?: number } = $props();

  const ipad = $derived(form === "ipad");
  const home = $derived(form === "home");
  const w = $derived(ipad ? 90 : 60);
  // Bildschirm: bei Home-Button-Geraeten mit breiten Raendern oben/unten.
  const screen = $derived(
    ipad ? { x: 6, y: 6, w: 78, h: 108, r: 5 }
    : home ? { x: 5, y: 17, w: 50, h: 86, r: 2 }
    : { x: 4, y: 4, w: 52, h: 112, r: 9 },
  );
  const uid = Math.random().toString(36).slice(2, 8);
</script>

<svg viewBox="0 0 {w} 120" style:height="{height}px" style:width="{(height * w) / 120}px" aria-hidden="true">
  <defs>
    <linearGradient id="frame-{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8a8e9c" />
      <stop offset="0.5" stop-color="#4b4f5c" />
      <stop offset="1" stop-color="#7c8090" />
    </linearGradient>
    <linearGradient id="wall-{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8b6cff" />
      <stop offset="0.6" stop-color="#5b8cff" />
      <stop offset="1" stop-color="#3ec9f0" />
    </linearGradient>
  </defs>

  <!-- Gehaeuse -->
  <rect x="0.5" y="0.5" width={w - 1} height="119" rx={home ? 9 : ipad ? 8 : 12}
        fill="url(#frame-{uid})" />
  <rect x="2" y="2" width={w - 4} height="116" rx={home ? 8 : ipad ? 7 : 11} fill="#0b0c10" />

  <!-- Bildschirm -->
  <rect x={screen.x} y={screen.y} width={screen.w} height={screen.h} rx={screen.r} fill="url(#wall-{uid})" />
  <rect x={screen.x} y={screen.y} width={screen.w} height={screen.h / 2} rx={screen.r} fill="#fff" opacity="0.08" />

  {#if form === "island"}
    <rect x="22" y="7.5" width="16" height="5" rx="2.5" fill="#0b0c10" />
  {:else if form === "notch"}
    <path d="M18 4 h24 v3 a4 4 0 0 1 -4 4 h-16 a4 4 0 0 1 -4 -4 z" fill="#0b0c10" />
  {:else if home}
    <rect x="23" y="9" width="14" height="2" rx="1" fill="#2a2d38" />
    <circle cx="30" cy="111.5" r="4.5" fill="none" stroke="#2a2d38" stroke-width="1.4" />
  {:else if ipad}
    <circle cx="45" cy="3.2" r="1" fill="#2a2d38" />
  {/if}
</svg>

<style>
  svg { display: block; flex: none; filter: drop-shadow(0 4px 10px rgb(0 0 0 / 0.35)); }
</style>
