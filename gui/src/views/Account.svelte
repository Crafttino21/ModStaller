<script lang="ts">
  import {
    LogOut, KeyRound, ShieldCheck, TriangleAlert, LoaderCircle, RefreshCw, Users, Smartphone, Trash2,
    UserPlus, CircleUser,
  } from "@lucide/svelte";
  import PageHeader from "../components/PageHeader.svelte";
  import { ask, errorText, refreshStatus, toast, ui } from "../lib/state.svelte";
  import { call } from "../lib/rpc";
  import { logout } from "../lib/actions";
  import { locale, t } from "../lib/i18n.svelte";
  import type { Account, AppId, Cert, Team } from "../lib/types";

  const loggedIn = $derived(ui.status?.loggedIn ?? false);
  const accounts = $derived(ui.status?.accounts ?? []);

  // -- Mehrere Accounts ----------------------------------------------------
  /** Welcher Account unten gezeigt wird - anfangs der aktive. */
  let chosen = $state<string | null>(null);
  const viewing = $derived(accounts.find((a) => a.adsid === chosen)
                           ?? accounts.find((a) => a.active) ?? null);
  /** Ein weiterer Account wird gerade angemeldet. */
  let adding = $state(false);

  function show(a: Account) {
    if (a.adsid === viewing?.adsid) return;
    chosen = a.adsid;
    forget();
  }

  function forget() {
    teams = null;
    certs = null;
    loadError = "";
  }

  async function makeActive(a: Account) {
    try {
      await call("accounts.setActive", { adsid: a.adsid });
      toast(t("{account} now signs new installs.", { account: a.label }));
      await refreshStatus(true);
    } catch (err) {
      toast(errorText(err), "bad", 8000);
    }
  }

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
      loginStep = t("Preparing Anisette …");
    try {
      await call("login", { appleId, password }, { onLog: (t) => (loginStep = t) });
      password = "";
      appleId = "";
      adding = false;
      // Der neue Account ist jetzt der aktive - ihn zeigen.
      chosen = null;
      forget();
      toast(t("Signed in."));
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
    const account = viewing?.adsid;
    if (!account) return;
    loading = true;
    loadError = "";
    try {
      const [tm, cs] = await Promise.all([
        call<Team[]>("account", { account }),
        call<{ teamId: string; certs: Cert[] }>("certs.list", { account }),
      ]);
      // Inzwischen auf einen anderen Account gewechselt? Dann gehoert das
      // Ergebnis nicht mehr hierher.
      if (account === viewing?.adsid) [teams, certs] = [tm, cs];
    } catch (err) {
      if (account === viewing?.adsid) loadError = errorText(err);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (viewing && teams === null && !loading && !loadError) load();
  });

  async function revoke(c: Cert) {
    const { ok } = await ask({
      title: t("Revoke certificate?"),
      text: c.name + "\n\n" + t("Every app signed with it will no longer start – including those of other sideloading tools."),
      confirm: t("Revoke"),
      danger: true,
    });
    if (!ok) return;
    try {
      await call("certs.revoke", { serial: c.serial, teamId: certs?.teamId, account: viewing?.adsid });
      toast(t("Certificate revoked."));
      load();
    } catch (err) {
      toast(errorText(err), "bad", 8000);
    }
  }

  async function deleteAppId(team: Team, a: AppId) {
    // Ehrlich bleiben: das Wochenkontingent zaehlt neu angelegte App-IDs,
    // nicht vorhandene. Loeschen raeumt auf - es macht nichts frei.
    const { ok } = await ask({
      title: t("Delete App ID?"),
      text: [
        a.identifier,
        !team.usageKnown
          ? t("Whether an app depends on it cannot be determined without a connected iPhone.")
          : a.inUse
            ? t("An installed app belongs to it – from ModStaller or from another tool. After deleting, it can no longer be renewed.")
            : t("No installed app belongs to this App ID right now."),
        t("This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself."),
      ].join("\n\n"),
      confirm: t("Delete"),
      danger: true,
    });
    if (!ok) return;
    try {
      await call("appids.delete", { appIdId: a.appIdId, teamId: team.teamId, account: viewing?.adsid });
      toast(t("App ID deleted."));
      load();
    } catch (err) {
      toast(errorText(err), "bad", 8000);
    }
  }

  async function doLogout(a: Account) {
    try {
      if (await logout(a, accounts.length === 1)) {
        if (chosen === a.adsid) chosen = null;
        forget();
        await refreshStatus(true);
      }
    } catch (err) {
      toast(errorText(err), "bad", 8000);
    }
  }
</script>

<PageHeader title={t("Apple account")} subtitle={t("Your Apple account signs the apps. The password is never stored or transmitted.")}>
  {#snippet actions()}
    {#if loggedIn && !adding}
      <button class="btn" onclick={load} disabled={loading}><RefreshCw size={16} /> {t("Refresh")}</button>
      <button class="btn" onclick={() => (adding = true)}><UserPlus size={16} /> {t("Add account")}</button>
    {/if}
  {/snippet}
</PageHeader>

{#if !loggedIn || adding}
  <div class="login-wrap">
    <form class="card login" onsubmit={login}>
      <div class="icon"><KeyRound size={24} /></div>
      <h2>{adding ? t("Add an Apple account") : t("Sign in with Apple")}</h2>
      <p class="muted">{adding
        ? t("It becomes the active account for new installs. Apps keep renewing with the account that installed them.")
        : t("An ordinary, free Apple ID is enough. Apple then asks for a code on your iPhone.")}</p>
      <div class="field">
        <label for="aid">Apple ID</label>
        <input id="aid" type="email" autocomplete="username" bind:value={appleId} disabled={loggingIn} />
      </div>
      <div class="field">
        <label for="pw">{t("Password")}</label>
        <input id="pw" type="password" autocomplete="current-password" bind:value={password} disabled={loggingIn} />
      </div>
      {#if loginError}
        <div class="banner bad small selectable"><TriangleAlert size={16} color="var(--bad)" /><div class="grow">{loginError}</div></div>
      {/if}
      <button class="btn primary big" type="submit" disabled={loggingIn || !appleId.trim() || !password}>
        {#if loggingIn}<LoaderCircle size={16} class="spin" /><span class="ellipsis" title={loginStep}>{loginStep}</span>{:else}{t("Sign in")}{/if}
      </button>
      {#if adding && !loggingIn}
        <button type="button" class="btn ghost" onclick={() => { adding = false; loginError = ""; }}>{t("Cancel")}</button>
      {/if}
      <p class="faint tiny"><ShieldCheck size={13} /> {t("SRP-6a: Apple gets proof that you know the password – not the password itself.")}</p>
    </form>
  </div>
{:else}
  <div class="card pad">
    <h2>{t("Signed-in accounts")}</h2>
    {#if accounts.length > 1}
      <p class="muted desc">{t("New installs sign with the active account. Renewals always use the account that installed the app.")}</p>
    {/if}
    <div class="accounts">
      {#each accounts as a (a.adsid)}
        <div class="acc" class:viewing={a.adsid === viewing?.adsid}>
          <button class="acc-main" onclick={() => show(a)} title={t("Show teams and certificates")}>
            <CircleUser size={20} />
            <div class="grow">
              <div class="acc-name selectable">{a.label}</div>
              {#if a.firstName && a.firstName !== a.label}<div class="faint tiny">{a.firstName}</div>{/if}
            </div>
          </button>
          {#if a.active}
            <span class="chip accent">{t("Active")}</span>
          {:else}
            <button class="btn sm" onclick={() => makeActive(a)}>{t("Make active")}</button>
          {/if}
          <button class="btn sm icon danger" title={t("Sign out")} onclick={() => doLogout(a)}><LogOut size={15} /></button>
        </div>
      {/each}
    </div>
  </div>

  {#if accounts.length > 1 && viewing}
    <p class="faint viewing-note">{t("Teams and certificates of {account}", { account: viewing.label })}</p>
  {/if}

  {#if loadError}
    <div class="banner bad small"><TriangleAlert size={16} color="var(--bad)" /><div class="grow selectable">{loadError}</div>
      <button class="btn sm" onclick={load}>{t("Again")}</button></div>
  {/if}

  {#if loading && !teams}
    <div class="card pad">
      <p class="muted tiny"><LoaderCircle size={14} class="spin" /> {t("Asking Apple – this takes a few seconds …")}</p>
      <div class="skeleton" style="height:22px;width:40%;margin-top:14px"></div>
      <div class="skeleton" style="height:70px;margin-top:14px"></div>
    </div>
  {/if}

  {#each teams ?? [] as team (team.teamId)}
    {@const used = team.appIds.length}
    {@const free = team.usageKnown ? team.appIds.filter((a) => !a.inUse).length : 0}
    {@const max = team.maxAppIdsPerWeek}
    <div class="card pad team">
      <div class="team-head">
        <div>
          <h2>{team.name}</h2>
          <p class="faint mono">{team.teamId} · {team.type}</p>
        </div>
        <span class="chip {team.isFree ? 'accent' : 'ok'}">{team.isFree ? t("Free") : t("Paid")}</span>
      </div>
      <p class="muted desc">{team.description}</p>

      <div class="metrics">
        <div class="metric">
          <div class="m-label"><Users size={15} /> {t("App IDs in the account")}</div>
          <div class="m-value">{used}{#if free}<span class="faint sub-value">· {t("{count} free", { count: free })}</span>{/if}</div>
          {#if max}
            <p class="faint quota">
              {@html t("Apple allows {max} <b>newly created</b> ones per week. Existing ones do not count – deleting therefore gives back no quota. When the window is full, ModStaller reuses a free one.", { max })}
            </p>
          {/if}
        </div>
        <div class="metric">
          <div class="m-label"><Smartphone size={15} /> {t("Registered devices")}</div>
          <div class="m-value">{team.devices}</div>
        </div>
      </div>

      {#if team.appIds.length}
        <details>
          <summary>{t("Manage App IDs ({count})", { count: used })}</summary>
          {#if !team.usageKnown}
            <div class="banner warn small hint">
              <div class="grow">{t("Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.")}</div>
            </div>
          {/if}
          <div class="ids">
            {#each team.appIds as a (a.appIdId)}
              <div class="id-row">
                <div class="grow">
                  <code class="selectable">{a.identifier}</code>
                  {#if a.name && a.name !== a.identifier}<div class="faint id-name">{a.name}</div>{/if}
                </div>
                {#if team.usageKnown}
                  <span class="chip {a.inUse ? 'ok' : ''}">{a.inUse ? t("in use") : t("free")}</span>
                {/if}
                <button class="btn sm icon danger" title={t("Delete App ID")}
                        onclick={() => deleteAppId(team, a)}><Trash2 size={15} /></button>
              </div>
            {/each}
          </div>
        </details>
      {/if}
    </div>
  {/each}

  {#if certs}
    <div class="card pad">
      <h2>{t("Development certificates")}</h2>
      <p class="muted desc">
        {t("Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.")}
      </p>
      {#if !certs.certs.length}
        <p class="faint">{t("No certificates in the account.")}</p>
      {:else}
        <div class="certs">
          {#each certs.certs as c (c.serial)}
            <div class="cert">
              <div class="grow">
                <div class="c-name">{c.name}</div>
                <div class="faint mono tiny">{c.certId}{#if c.expiresAt} · {t("expires {date}", { date: new Date(c.expiresAt).toLocaleDateString(locale()) })}{/if}</div>
              </div>
              <button class="btn sm danger" onclick={() => revoke(c)}>{t("Revoke")}</button>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
{/if}

<style>
  .login-wrap { display: grid; place-items: center; padding-top: 10px; }
  .login { width: min(420px, 100%); padding: 28px; display: grid;
           grid-template-columns: minmax(0, 1fr); gap: 14px; }
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
  .sub-value { margin-left: 8px; font-size: 15px; font-weight: 550; }
  .quota { margin: 0; font-size: 12px; line-height: 1.45; }
  details { margin-top: 14px; }
  summary { cursor: pointer; font-size: 12.5px; color: var(--text-2); font-weight: 550; }
  .hint { margin-top: 10px; }
  .ids { display: grid; margin-top: 10px; }
  .id-row { display: flex; align-items: center; gap: 10px; padding: 9px 0; }
  .id-row + .id-row { border-top: 1px solid var(--border); }
  .id-row .grow { flex: 1; min-width: 0; }
  .id-row code { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                 color: var(--text-2); }
  .id-name { font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .certs { display: grid; margin-top: 14px; }
  .cert { display: flex; align-items: center; gap: 12px; padding: 12px 0; }
  .cert + .cert { border-top: 1px solid var(--border); }
  .c-name { font-weight: 550; }
  .accounts { display: grid; margin-top: 12px; }
  .acc { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 10px; }
  .acc + .acc { margin-top: 4px; }
  .acc.viewing { background: var(--surface-2); }
  .acc-main { flex: 1; min-width: 0; display: flex; align-items: center; gap: 10px; background: none; border: 0;
              padding: 0; color: inherit; font: inherit; text-align: left; cursor: pointer; }
  .acc-name { font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .viewing-note { margin: 0 4px 10px; font-size: 12.5px; }
</style>
