<script lang="ts">
  // Ein kleines Symbol je Geraeteart - fuer Listen, wo das Mockup zu gross ist.
  import { Smartphone, Tablet, Tv, Glasses } from "@lucide/svelte";

  let { platform = "ios", formFactor = "island", size = 16 }:
    { platform?: string; formFactor?: string; size?: number } = $props();
</script>

{#if platform === "tvos"}<Tv {size} />
{:else if platform === "xros"}<Glasses {size} />
{:else if formFactor === "ipad"}<Tablet {size} />
{:else}<Smartphone {size} />{/if}
