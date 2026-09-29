<script lang="ts">
  // Gezeichnetes Geraet in der Bauform des echten: Home-Button, Notch oder
  // Dynamic Island - oder ein Fernseher fuers Apple TV. Bewusst kein
  // Produktfoto - nur die Silhouette.
  let { form = "island", height = 64 }: { form?: string; height?: number } = $props();

  const tv = $derived(form === "tv");
  const vision = $derived(form === "vision");
  const ipad = $derived(form === "ipad");
  // Der iPod touch hat den Koerper eines iPhones mit Home-Button - nur schmaler.
  const ipod = $derived(form === "ipod");
  const home = $derived(form === "home" || ipod);
  const w = $derived(ipad ? 90 : ipod ? 54 : 60);
  // Bildschirm: bei Home-Button-Geraeten mit breiten Raendern oben/unten.
  const screen = $derived(
    ipad ? { x: 6, y: 6, w: 78, h: 108, r: 5 }
    : ipod ? { x: 5, y: 17, w: 44, h: 86, r: 2 }
    : home ? { x: 5, y: 17, w: 50, h: 86, r: 2 }
    : { x: 4, y: 4, w: 52, h: 112, r: 9 },
  );
  const uid = Math.random().toString(36).slice(2, 8);
</script>

{#if vision}
<svg viewBox="0 0 170 120" style:height="{height}px" style:width="{(height * 170) / 120}px" aria-hidden="true">
  <defs>
    <linearGradient id="wall-{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8b6cff" />
      <stop offset="0.6" stop-color="#5b8cff" />
      <stop offset="1" stop-color="#3ec9f0" />
    </linearGradient>
  </defs>
  <!-- Kopfband -->
  <path d="M8 62 C 8 40, 40 34, 85 34 C 130 34, 162 40, 162 62" fill="none" stroke="#4b4f5c" stroke-width="7"
        stroke-linecap="round" />
  <!-- Front: gewoelbtes Glas -->
  <path d="M22 50 C 22 38, 50 32, 85 32 C 120 32, 148 38, 148 50 L 148 76 C 148 92, 124 98, 108 94
           C 98 91, 94 84, 85 84 C 76 84, 72 91, 62 94 C 46 98, 22 92, 22 76 Z" fill="#0b0c10" stroke="#6a6e7c"
        stroke-width="2.5" />
  <path d="M30 52 C 30 43, 55 39, 85 39 C 115 39, 140 43, 140 52 L 140 72 C 140 84, 122 88, 110 86
           C 100 84, 96 77, 85 77 C 74 77, 70 84, 60 86 C 48 88, 30 84, 30 72 Z" fill="url(#wall-{uid})" opacity="0.9" />
  <path d="M30 52 C 30 43, 55 39, 85 39 C 115 39, 140 43, 140 52 L 140 58 C 110 54, 60 54, 30 58 Z"
        fill="#fff" opacity="0.12" />
</svg>
{:else if tv}
<svg viewBox="0 0 170 120" style:height="{height}px" style:width="{(height * 170) / 120}px" aria-hidden="true">
  <defs>
    <linearGradient id="wall-{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8b6cff" />
      <stop offset="0.6" stop-color="#5b8cff" />
      <stop offset="1" stop-color="#3ec9f0" />
    </linearGradient>
  </defs>
  <!-- Fernseher -->
  <rect x="1" y="6" width="168" height="98" rx="6" fill="#4b4f5c" />
  <rect x="3" y="8" width="164" height="94" rx="5" fill="#0b0c10" />
  <rect x="6" y="11" width="158" height="88" rx="3" fill="url(#wall-{uid})" />
  <rect x="6" y="11" width="158" height="44" rx="3" fill="#fff" opacity="0.08" />
  <!-- Fuss -->
  <rect x="75" y="104" width="20" height="8" fill="#4b4f5c" />
  <rect x="58" y="111" width="54" height="5" rx="2.5" fill="#6a6e7c" />
</svg>
{:else}
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
    <rect x={w / 2 - 7} y="9" width="14" height="2" rx="1" fill="#2a2d38" />
    <circle cx={w / 2} cy="111.5" r="4.5" fill="none" stroke="#2a2d38" stroke-width="1.4" />
  {:else if ipad}
    <circle cx="45" cy="3.2" r="1" fill="#2a2d38" />
  {/if}
</svg>
{/if}

<style>
  svg { display: block; flex: none; filter: drop-shadow(0 4px 10px rgb(0 0 0 / 0.35)); }
</style>
