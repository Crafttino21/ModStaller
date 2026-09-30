<script lang="ts" module>
  // Bilder aus Store-Quellen holt das Backend (store.image) - die CSP laesst
  // nur eigene Bilder und data:-URLs zu. Einmal geholt, bleiben sie hier.
  const cache = new Map<string, Promise<string | null>>();

  function load(url: string, kind: string): Promise<string | null> {
    const key = `${kind}|${url}`;
    let hit = cache.get(key);
    if (!hit) {
      hit = call<string>("store.image", { url, kind }).catch(() => null);
      cache.set(key, hit);
    }
    return hit;
  }
</script>

<script lang="ts">
  import { call } from "../lib/rpc";

  let { url = "", kind = "icon", alt = "", fallback = "", class: cls = "" }:
    { url?: string; kind?: "icon" | "screenshot"; alt?: string; fallback?: string; class?: string } = $props();

  let el = $state<HTMLElement | null>(null);
  let src = $state<string | null>(null);
  let visible = $state(false);

  // Erst holen, wenn es ins Bild kommt - ein Raster mit hundert Apps soll
  // nicht hundert Bilder auf einmal anfragen.
  $effect(() => {
    if (!el) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        visible = true;
        io.disconnect();
      }
    }, { rootMargin: "200px" });
    io.observe(el);
    return () => io.disconnect();
  });

  $effect(() => {
    src = null;
    if (!visible || !url) return;
    let stale = false;
    load(url, kind).then((d) => { if (!stale) src = d; });
    return () => { stale = true; };
  });
</script>

<div bind:this={el} class="img {cls}" class:shot={kind === "screenshot"}>
  {#if src}
    <img {src} {alt} />
  {:else}
    <span class="ph">{fallback.slice(0, 1).toUpperCase()}</span>
  {/if}
</div>

<style>
  .img { display: grid; place-items: center; overflow: hidden; background: var(--surface-2); flex: none; }
  .img img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .shot img { object-fit: contain; }
  .ph { font-weight: 700; color: var(--text-3); font-size: 1.1em; }
</style>
