<script lang="ts">
  import {
    LogOut, KeyRound, ShieldCheck, TriangleAlert, LoaderCircle, RefreshCw, Users, Smartphone,
  } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { ask, errorText, refreshStatus, toast, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { logout } from "../lib/actions";
  import type { Cert, Team } from "../lib/types";

  const loggedIn = $derived(ui.status?.loggedIn ?? false);

  // -- Anmeldung -----------------------------------------------------------
  let appleId = $state("");
  let password = $state("");
  let loggingIn = $state(false);
  let loginStep = $state("");
  let loginError = $state("");

  async function login(e: Event) {
    e.preventDefault();
    loggingIn = true;
    loginError = "";
    loginStep = "Anisette vorbereiten …";
    try {
      await call("login", { appleId, password }, { onLog: (t) => (loginStep = t) });
      password = "";
      toast("Angemeldet.");
      await refreshStatus(true);
    } catch (err) {
      loginError = errorText(err);
    } finally {
      loggingIn = false;
    }
  }

  // -- Konto ---------------------------------------------------------------
  let teams = $state<Team[] | null>(null);
  let certs = $state<{ teamId: string; certs: Cert[] } | null>(null);
  let loadError = $state("");
  let loading = $state(false);

  async function load() {
    loading = true;
    loadError = "";
    try {
      [teams, certs] = await Promise.all([
        call<Team[]>("account"),
        call<{ teamId: string; certs: Cert[] }>("certs.list"),
      ]);
    } catch (err) {
      loadError = errorText(err);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (loggedIn && teams === null && !loading && !loadError) load();
  });

  async function revoke(c: Cert) {
    const { ok } = await ask({
      title: "Zertifikat widerrufen?",
      text: `${c.name}\n\nAlle Apps, die damit signiert wurden, starten danach nicht mehr – auch die anderer Sideload-Werkzeuge.`,
      confirm: "Widerrufen",
      danger: true,
    });
    if (!ok) return;
    try {
      await call("certs.revoke", { serial: c.serial, teamId: certs?.teamId });
      toast("Zertifikat widerrufen.");
      load();
    } catch (err) {
      toast(errorText(err), "bad", 8000);
    }
  }

  async function doLogout() {
    if (await logout()) {
      teams = null;
      certs = null;
      await refreshStatus(true);
    }
  }
</script>

<PageHeader title="Apple-Konto" subtitle="Dein Apple-Account signiert die Apps. Das Passwort wird nie gespeichert oder übertragen.">
  {#snippet actions()}
    {#if loggedIn}
      <button class="btn" onclick={load} disabled={loading}><RefreshCw size={16} /> Aktualisieren</button>
      <button class="btn danger" onclick={doLogout}><LogOut size={16} /> Abmelden</button>
    {/if}
  {/snippet}
</PageHeader>

{#if !loggedIn}
  <div class="login-wrap">
    <form class="card login" onsubmit={login}>
      <div class="icon"><KeyRound size={24} /></div>
      <h2>Bei Apple anmelden</h2>
      <p class="muted">Eine normale, kostenlose Apple ID reicht. Danach fragt Apple einen Code auf deinem iPhone ab.</p>
      <div class="field">
        <label for="aid">Apple ID</label>
        <input id="aid" type="email" autocomplete="username" bind:value={appleId} disabled={loggingIn} />
      </div>
      <div class="field">
        <label for="pw">Passwort</label>
        <input id="pw" type="password" autocomplete="current-password" bind:value={password} disabled={loggingIn} />
      </div>
      {#if loginError}
        <div class="banner bad small selectable"><TriangleAlert size={16} color="var(--bad)" /><div class="grow">{loginError}</div></div>
      {/if}
      <button class="btn primary big" type="submit" disabled={loggingIn || !appleId.trim() || !password}>
        {#if loggingIn}<LoaderCircle size={16} class="spin" /> {loginStep}{:else}Anmelden{/if}
      </button>
      <p class="faint tiny"><ShieldCheck size={13} /> SRP-6a: Apple bekommt einen Beweis, dass du das Passwort kennst – nicht das Passwort selbst.</p>
    </form>
  </div>
{:else}
  {#if loadError}
    <div class="banner bad small"><TriangleAlert size={16} color="var(--bad)" /><div class="grow selectable">{loadError}</div>
      <button class="btn sm" onclick={load}>Erneut</button></div>
  {/if}

  {#if loading && !teams}
    <div class="card pad">
      <p class="muted tiny"><LoaderCircle size={14} class="spin" /> Bei Apple nachfragen – das dauert ein paar Sekunden …</p>
      <div class="skeleton" style="height:22px;width:40%;margin-top:14px"></div>
      <div class="skeleton" style="height:70px;margin-top:14px"></div>
    </div>
  {/if}

  {#each teams ?? [] as t (t.teamId)}
    {@const used = t.appIds.length}
    {@const max = t.maxAppIdsPerWeek}
    <div class="card pad team">
      <div class="team-head">
        <div>
          <h2>{t.name}</h2>
          <p class="faint mono">{t.teamId} · Typ {t.type}</p>
        </div>
        <span class="chip {t.isFree ? 'accent' : 'ok'}">{t.isFree ? "Kostenlos" : "Bezahlt"}</span>
      </div>
      <p class="muted desc">{t.description}</p>

      <div class="metrics">
        <div class="metric">
          <div class="m-label"><Users size={15} /> App-IDs</div>
          <div class="m-value">{used}{#if max}<span class="faint"> / {max}</span>{/if}</div>
          {#if max}
            <div class="meter"><div class:full={used >= max} style:width="{Math.min(100, (used / max) * 100)}%"></div></div>
            <div class="faint tiny">
              {used >= max ? "Ausgeschöpft – ModStaller nutzt vorhandene App-IDs weiter." : `Noch ${max - used} frei (zählt neu angelegte pro Woche)`}
            </div>
          {/if}
        </div>
        <div class="metric">
          <div class="m-label"><Smartphone size={15} /> Registrierte Geräte</div>
          <div class="m-value">{t.devices}</div>
        </div>
      </div>

      {#if t.appIds.length}
        <details>
          <summary>App-IDs anzeigen</summary>
          <div class="ids selectable">{#each t.appIds as id}<code>{id}</code>{/each}</div>
        </details>
      {/if}
    </div>
  {/each}

  {#if certs}
    <div class="card pad">
      <h2>Development-Zertifikate</h2>
      <p class="muted desc">
        Apple erlaubt nur wenige gleichzeitig. Ein fremdes (z.&nbsp;B. von AltStore oder SideStore) kann ModStaller nicht
        mitbenutzen – der private Schlüssel liegt beim anfordernden Werkzeug.
      </p>
      {#if !certs.certs.length}
        <p class="faint">Keine Zertifikate im Account.</p>
      {:else}
        <div class="certs">
          {#each certs.certs as c (c.serial)}
            <div class="cert">
              <div class="grow">
                <div class="c-name">{c.name}</div>
                <div class="faint mono tiny">{c.certId}{#if c.expiresAt} · läuft ab {new Date(c.expiresAt).toLocaleDateString("de-DE")}{/if}</div>
              </div>
              <button class="btn sm danger" onclick={() => revoke(c)}>Widerrufen</button>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
{/if}

<style>
  .login-wrap { display: grid; place-items: center; padding-top: 10px; }
  .login { width: min(420px, 100%); padding: 28px; display: grid; gap: 14px; }
  .login .icon { width: 50px; height: 50px; border-radius: 14px; display: grid; place-items: center; background: var(--accent-grad); color: #fff; }
  .login p { font-size: 13px; }
  .big { height: 42px; margin-top: 4px; }
  .tiny { font-size: 12px; display: flex; gap: 5px; align-items: center; }
  .small { font-size: 13px; }
  .grow { flex: 1; min-width: 0; }
  .pad { padding: 22px; margin-bottom: 14px; }
  .team-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .team-head p { margin-top: 3px; font-size: 12px; }
  .desc { margin-top: 10px; font-size: 13px; }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 18px; }
  .metric { padding: 14px 16px; border-radius: 12px; background: var(--surface-2); display: grid; gap: 6px; }
  .m-label { display: flex; gap: 7px; align-items: center; font-size: 12.5px; color: var(--text-2); font-weight: 550; }
  .m-value { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .meter { height: 6px; border-radius: 99px; background: var(--border); overflow: hidden; }
  .meter div { height: 100%; background: var(--accent-grad); border-radius: inherit; }
  .meter div.full { background: var(--warn); }
  details { margin-top: 14px; }
  summary { cursor: pointer; font-size: 12.5px; color: var(--text-2); font-weight: 550; }
  .ids { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .ids code { padding: 3px 8px; border-radius: 6px; background: var(--surface-2); color: var(--text-2); }
  .certs { display: grid; margin-top: 14px; }
  .cert { display: flex; align-items: center; gap: 12px; padding: 12px 0; }
  .cert + .cert { border-top: 1px solid var(--border); }
  .c-name { font-weight: 550; }
</style>
