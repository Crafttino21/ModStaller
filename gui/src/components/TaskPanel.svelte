<script lang="ts">
  import { CircleCheck, CircleX, LoaderCircle, Ban, Minimize2, Info } from "@lucide/svelte";
  import Modal from "./Modal.svelte";
  import { closeTask, ui } from "../lib/state.svelte";
  import { locale, t } from "../lib/i18n.svelte";

  const task = $derived(ui.task!);
  let logEl = $state<HTMLDivElement | undefined>();

  // Welches fremde Zertifikat weichen darf - bewusst ohne Vorauswahl: es
  // legt die Apps eines anderen Werkzeugs still. Nur was in der aktuellen
  // Liste steht, zaehlt (nach einem zweiten Anlauf ist es eine neue).
  let revoke = $state("");
  const picked = $derived(task.conflict?.some((c) => c.serial === revoke) ? revoke : "");

  // Eigener Zustand statt open={...}: sonst setzt Svelte das Attribut bei
  // jeder neuen Zeile neu - und klappt das Protokoll wieder zu, das man
  // gerade aufgemacht hat. Bei einem Fehler geht es einmal von selbst auf.
  let logOpen = $state(false);
  $effect(() => {
    if (task.state === "error") logOpen = true;
  });

  // Neuestes immer sichtbar halten.
  $effect(() => {
    task.log.length;
    if (logEl) logEl.scrollTop = logEl.scrollHeight;
  });
</script>

<Modal width={620} onclose={closeTask}>
  <div class="head">
    <div class="state {task.state}">
      {#if task.state === "running"}
        <LoaderCircle size={22} class="spin" />
      {:else if task.state === "done"}
        <CircleCheck size={22} />
      {:else if task.state === "cancelled"}
        <Ban size={22} />
      {:else}
        <CircleX size={22} />
      {/if}
    </div>
    <div class="grow">
      <h2>{task.title}</h2>
      <p class="muted">
        {#if task.state === "running"}
          {task.log.at(-1) ?? t("Starting …")}
        {:else}
          {task.state === "done" ? t("Done") : task.state === "cancelled" ? t("Cancelled") : t("Failed")}
        {/if}
      </p>
    </div>
  </div>

  {#if task.state === "running" && task.pct !== null}
    <div class="bar"><div style:width="{task.pct}%"></div></div>
    <div class="pct faint">{t("{percent}% transferred", { percent: task.pct })}</div>
  {:else if task.state === "running"}
    <div class="bar indeterminate"><div></div></div>
  {/if}

  {#if task.kind === "jit" && task.state === "running"}
    <div class="banner info hint">
      <Info size={18} />
      <div class="grow">
        {t("Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.")}
      </div>
    </div>
  {/if}

  {#if task.state !== "running" && task.message}
    <div class="result {task.state} {task.tone} selectable">{task.message}</div>
  {/if}
  {#each task.notes as note}
    <p class="note muted selectable">{note}</p>
  {/each}

  {#if task.state === "error" && task.conflict}
    <div class="conflict">
      <div class="c-head">{t("Which certificate may go?")}</div>
      {#each task.conflict as c (c.serial)}
        <label class="cert" class:picked={picked === c.serial}>
          <input type="radio" name="revoke" value={c.serial} bind:group={revoke} />
          <div class="grow">
            <div class="c-name">{c.name}</div>
            <div class="faint mono">{c.certId}{#if c.expiresAt} · {t("expires {date}", { date: new Date(c.expiresAt).toLocaleDateString(locale()) })}{/if}</div>
          </div>
        </label>
      {/each}
      <p class="note muted">
        {t("The name is the computer or device that requested it.")}
        {t("Every app signed with it will no longer start – including those of other sideloading tools.")}
      </p>
    </div>
  {/if}

  <details bind:open={logOpen}>
    <summary>{t("Log")} ({task.log.length})</summary>
    <div class="log selectable" bind:this={logEl}>
      {#each task.log as line}
        <div>{line}</div>
      {:else}
        <div class="faint">{t("No messages yet.")}</div>
      {/each}
    </div>
  </details>

  <div class="actions">
    {#if task.state === "running"}
      <button class="btn ghost" onclick={closeTask}><Minimize2 size={16} /> {t("In the background")}</button>
      <button class="btn danger" onclick={() => task.call.cancel()}>{t("Cancel")}</button>
    {:else if task.state === "error" && task.conflict}
      <button class="btn ghost" onclick={closeTask}>{t("Close")}</button>
      <button class="btn danger solid" disabled={!picked}
              onclick={() => task.retry({ revokeCertificate: picked })}>{t("Revoke and try again")}</button>
    {:else}
      <button class="btn primary" onclick={closeTask}>{t("Close")}</button>
    {/if}
  </div>
</Modal>

<style>
  .head { display: flex; gap: 14px; align-items: flex-start; }
  .head p { margin-top: 3px; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 480px; }
  .grow { flex: 1; min-width: 0; }
  .state { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; flex: none; }
  .state.running { background: var(--accent-soft); color: var(--accent); }
  .state.done { background: var(--ok-soft); color: var(--ok); }
  .state.error { background: var(--bad-soft); color: var(--bad); }
  .state.cancelled { background: var(--warn-soft); color: var(--warn); }

  .bar { height: 8px; margin-top: 20px; border-radius: 99px; background: var(--surface-2); overflow: hidden; }
  .bar div { height: 100%; background: var(--accent-grad); border-radius: inherit; transition: width 0.3s ease; }
  .bar.indeterminate div { width: 35%; animation: slide 1.3s ease-in-out infinite; }
  @keyframes slide { from { transform: translateX(-100%); } to { transform: translateX(290%); } }
  .pct { font-size: 12px; margin-top: 6px; font-variant-numeric: tabular-nums; }

  .hint { margin-top: 18px; font-size: 13px; }
  .hint :global(svg) { color: var(--accent); flex: none; }

  .result { margin-top: 18px; padding: 12px 14px; border-radius: 10px; white-space: pre-wrap; font-size: 13.5px; }
  .result.done { background: var(--ok-soft); }
  .result.done.warn { background: var(--warn-soft); }
  .result.error { background: var(--bad-soft); }
  .result.cancelled { background: var(--warn-soft); }
  .note { margin-top: 8px; font-size: 13px; }

  .conflict { margin-top: 16px; }
  .c-head { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
  .cert {
    display: flex; align-items: center; gap: 12px; padding: 10px 12px; margin-top: 6px;
    border: 1px solid var(--border); border-radius: 10px; cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }
  .cert:hover { border-color: var(--text-3); }
  .cert.picked { border-color: var(--bad); background: var(--bad-soft); }
  .cert input { accent-color: var(--bad); width: 16px; height: 16px; flex: none; margin: 0; }
  .c-name { font-weight: 550; font-size: 13.5px; }
  .cert .mono { font-size: 12px; }

  details { margin-top: 18px; }
  summary { cursor: pointer; color: var(--text-2); font-size: 12.5px; font-weight: 550; }
  .log {
    margin-top: 8px; max-height: 220px; overflow: auto;
    padding: 12px 14px; border-radius: 10px;
    background: var(--bg); border: 1px solid var(--border);
    font-family: var(--mono); font-size: 12px; line-height: 1.6; white-space: pre-wrap;
  }

  .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 22px; }
</style>
