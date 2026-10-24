<script lang="ts">
  // Nach einem Update: was die neue Version bringt (lib/whatsnew.ts).
  import { ExternalLink, ShieldCheck, Sparkles } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { closeWhatsNew, ui } from "../lib/state.svelte";
  import { t } from "../lib/i18n.svelte";

  const RELEASES_URL = "https://github.com/Crafttino21/ModStaller/releases";

  const releases = $derived(ui.whatsNew!);
</script>

<Modal width={540} onclose={closeWhatsNew}>
  <div class="head">
    <div class="icon"><Sparkles size={22} /></div>
    <h2>{t("What's new in ModStaller {version}", { version: ui.update.current ?? releases[0].version })}</h2>
  </div>

  {#each releases as r (r.version)}
    {#if releases.length > 1}<h3>{t("Version {version}", { version: r.version })}</h3>{/if}
    {#if r.highlight}
      <div class="highlight selectable"><ShieldCheck size={18} /><p>{t(r.highlight)}</p></div>
    {/if}
    {#if r.items.length}
      <ul class="selectable">
        {#each r.items as item}<li>{t(item)}</li>{/each}
      </ul>
    {/if}
  {/each}

  <div class="actions">
    <a class="btn ghost" href={RELEASES_URL} target="_blank" rel="noreferrer">
      <ExternalLink size={15} /> {t("All changes on GitHub")}
    </a>
    <button class="btn primary" onclick={closeWhatsNew}>{t("Got it")}</button>
  </div>
</Modal>

<style>
  .head { display: flex; gap: 14px; align-items: center; }
  .icon { width: 42px; height: 42px; flex: none; border-radius: 12px; display: grid; place-items: center;
          background: var(--accent-grad); color: #fff; }
  h3 { margin-top: 20px; font-size: 13px; font-weight: 600; color: var(--text-2); }
  .highlight {
    display: flex; gap: 10px; align-items: flex-start; margin-top: 18px; padding: 12px 14px;
    border-radius: 10px; background: var(--ok-soft); font-size: 13.5px; line-height: 1.5;
  }
  .highlight :global(svg) { color: var(--ok); flex: none; margin-top: 1px; }
  ul { margin: 14px 0 0; padding-left: 20px; display: grid; gap: 8px; font-size: 13.5px; line-height: 1.5; }
  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 22px; }
</style>
