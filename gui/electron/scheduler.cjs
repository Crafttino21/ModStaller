// Wann der Hintergrundbetrieb erinnert, erneuert und Updates einspielt.
//
// Reine Logik ohne Electron: main.cjs holt den Status vom Backend, fragt hier
// nach, was zu tun ist, und fuehrt es aus. Was schon gemeldet wurde, steht in
// `memory` (userData/daemon-state.json) - so kommt eine Erinnerung auch nach
// einem Neustart nicht doppelt.
//
// Zeiten: `now` in Millisekunden, `expiresAt` wie vom Backend in Sekunden.

const HOUR = 3600 * 1000;
const DAY = 24 * HOUR;

/** Laenger abgelaufen als das: vermutlich laengst vom iPhone geloescht. Nicht
 *  ungefragt wieder aufspielen. */
const STALE_AFTER = 7 * DAY;
/** "iPhone anstecken" hoechstens so oft. */
const DEVICE_NAG_EVERY = 6 * HOUR;
/** Ab so vielen Fehlschlaegen in Folge gibt es eine Meldung. */
const FAILURES_BEFORE_NOTICE = 2;
/** Updates nur, wenn ModStaller so lange nicht benutzt wurde (Fenster zu) ... */
const UPDATE_IDLE_SECONDS = 10 * 60;
/** ... und in dieser Zeit kein Refresh ansteht. */
const UPDATE_REFRESH_MARGIN = 2 * HOUR;

/** Fehler, die ein Mensch beheben muss - gleich melden, nicht erst beim
 *  zweiten Mal. */
const NEEDS_PERSON = new Set(["NotPaired", "DeveloperModeDisabled", "SigningError", "UsbServiceUnavailable"]);
/** Die Anmeldung ist abgelaufen oder verlangt 2FA. */
const NEEDS_SIGN_IN = new Set(["InteractionRequired", "AppleError"]);

function emptyMemory() {
  return { reminded: {}, blocked: {}, nextTryAt: {}, failures: {}, deviceNaggedAt: 0, trayHintShown: false };
}

/** Gespeicherter Stand - unbekannte oder kaputte Teile fallen weg. */
function normalizeMemory(raw) {
  const m = emptyMemory();
  if (!raw || typeof raw !== "object") return m;
  for (const key of ["reminded", "blocked", "nextTryAt", "failures"]) {
    if (raw[key] && typeof raw[key] === "object" && !Array.isArray(raw[key])) m[key] = { ...raw[key] };
  }
  if (Number.isFinite(raw.deviceNaggedAt)) m.deviceNaggedAt = raw.deviceNaggedAt;
  if (raw.trayHintShown === true) m.trayHintShown = true;
  return m;
}

function msLeft(app, now) {
  return app.expiresAt * 1000 - now;
}

/** Ist das iPhone der App angesteckt? Alte Eintraege ohne UDID: irgendeins. */
function deviceAttached(app, attached) {
  if (!attached?.length) return false;
  return !app.udid || attached.includes(app.udid);
}

/** Warum die App ohne den Nutzer nicht erneuert werden kann - oder null. */
function blocker(app) {
  if (app.sourceMissing) return "ipa";
  if (app.accountReady === false) return "account";
  return null;
}

/**
 * Was jetzt zu tun ist.
 *
 * Gibt die Aktionen zurueck und den neuen `memory` - der geht davon aus, dass
 * die Meldungen auch gezeigt werden. Refreshes zaehlen erst mit
 * `onRefreshResult`.
 */
function plan({ apps = [], attached = [], now, prefs, memory }) {
  const next = normalizeMemory(memory);
  const out = {
    remind: [],            // Apps, an die jetzt erinnert wird
    refresh: [],           // jetzt erneuern
    waitingForDevice: [],  // faellig, aber das iPhone fehlt
    notifyDevice: false,   // "iPhone anstecken" jetzt zeigen
    blocked: [],           // [{app, reason}] - gerade neu gemeldet
    memory: next,
  };

  // Aufraeumen: Eintraege zu Apps, die es nicht mehr gibt oder die schon
  // erneuert wurden (anderes expiresAt), fallen weg.
  const current = new Map(apps.map((a) => [a.bundleId, a]));
  for (const key of ["reminded", "blocked"]) {
    for (const id of Object.keys(next[key])) {
      if (current.get(id)?.expiresAt !== next[key][id]) delete next[key][id];
    }
  }
  for (const key of ["nextTryAt", "failures"]) {
    for (const id of Object.keys(next[key])) if (!current.has(id)) delete next[key][id];
  }
  for (const id of Object.keys(next.failures)) {
    if (next.failures[id]?.expiresAt !== current.get(id).expiresAt) delete next.failures[id];
  }

  const remindWindow = prefs.remindDaysBefore * DAY;
  const refreshWindow = prefs.refreshHoursBefore * HOUR;

  for (const app of apps) {
    const left = msLeft(app, now);
    if (left < -STALE_AFTER) continue;

    if (prefs.remind && left > 0 && left <= remindWindow && next.reminded[app.bundleId] !== app.expiresAt) {
      next.reminded[app.bundleId] = app.expiresAt;
      // Schon im Refresh-Fenster: dann meldet sich der Refresh selbst (oder
      // "iPhone anstecken") - nicht zweimal fuer dieselbe App.
      if (!(prefs.autoRefresh && left <= prefs.refreshHoursBefore * HOUR)) out.remind.push(app);
    }

    if (!prefs.autoRefresh || left > refreshWindow) continue;

    const reason = blocker(app);
    if (reason) {
      if (next.blocked[app.bundleId] !== app.expiresAt) {
        next.blocked[app.bundleId] = app.expiresAt;
        out.blocked.push({ app, reason });
      }
      continue;
    }
    if (!deviceAttached(app, attached)) {
      out.waitingForDevice.push(app);
      continue;
    }
    if ((next.nextTryAt[app.bundleId] ?? 0) > now) continue;
    out.refresh.push(app);
  }

  if (out.waitingForDevice.length && now - next.deviceNaggedAt >= DEVICE_NAG_EVERY) {
    next.deviceNaggedAt = now;
    out.notifyDevice = true;
  }
  if (!out.waitingForDevice.length) next.deviceNaggedAt = 0;   // beim naechsten Mal gleich melden
  return out;
}

/** "Jetzt erneuern" aus dem Tray: alles, was ohne den Nutzer geht und dessen
 *  iPhone da ist - ohne Zeitfenster und Wartezeiten. */
function manualPlan({ apps = [], attached = [], now }) {
  return apps.filter((a) => msLeft(a, now) > -STALE_AFTER && !blocker(a) && deviceAttached(a, attached));
}

/**
 * Nach einem Refresh: Wartezeiten und Fehlerzaehler.
 *
 * `error` ist die JSON-RPC-Fehlerantwort (mit `data.kind` vom Backend) oder
 * null. Gibt `{memory, notify}` zurueck; `notify` ist null, "failed" oder
 * "signIn".
 */
function onRefreshResult(memory, app, error, now) {
  const next = normalizeMemory(memory);
  const id = app.bundleId;
  if (!error) {
    delete next.nextTryAt[id];
    delete next.failures[id];
    delete next.blocked[id];
    return { memory: next, notify: null };
  }
  const kind = error.data?.kind;
  if (!kind && error.code === -32800) {         // abgebrochen, etwa beim Beenden
    return { memory: next, notify: null };
  }
  if (kind === "DeviceNotFound") {
    // Kurz vorher noch da - gleich wieder, sobald es sich meldet.
    next.nextTryAt[id] = now + 5 * 60 * 1000;
    return { memory: next, notify: null };
  }

  const prev = next.failures[id]?.expiresAt === app.expiresAt ? next.failures[id].count : 0;
  const count = prev + 1;
  next.failures[id] = { expiresAt: app.expiresAt, count };

  if (NEEDS_SIGN_IN.has(kind)) {
    next.nextTryAt[id] = now + 6 * HOUR;
    // Einmal pro Ablauf - wie die anderen Hindernisse.
    if (next.blocked[id] === app.expiresAt) return { memory: next, notify: null };
    next.blocked[id] = app.expiresAt;
    return { memory: next, notify: "signIn" };
  }
  next.nextTryAt[id] = now + (kind === "AppleRateLimited" ? 2 * HOUR : HOUR);
  const threshold = NEEDS_PERSON.has(kind) ? 1 : FAILURES_BEFORE_NOTICE;
  return { memory: next, notify: count === threshold ? "failed" : null };
}

/** Nach einer neuen Anmeldung: alle Wartezeiten wegen der Anmeldung vergessen. */
function forgetBackoff(memory) {
  const next = normalizeMemory(memory);
  next.nextTryAt = {};
  next.failures = {};
  next.blocked = {};
  return next;
}

/** Wann der naechste Refresh faellig wird (ms) - oder null. */
function nextRefreshAt(apps, prefs, now) {
  if (!prefs.autoRefresh) return null;
  let best = null;
  for (const app of apps) {
    if (msLeft(app, now) < -STALE_AFTER || blocker(app)) continue;
    const at = app.expiresAt * 1000 - prefs.refreshHoursBefore * HOUR;
    if (best === null || at < best) best = at;
  }
  return best;
}

/** Die App, die als naechste ablaeuft (fuer den Tray) - oder null. */
function nextExpiring(apps, now) {
  let best = null;
  for (const app of apps) {
    if (msLeft(app, now) < -STALE_AFTER) continue;
    if (!best || app.expiresAt < best.expiresAt) best = app;
  }
  return best;
}

/**
 * Darf ein fertig geladenes Update jetzt still eingespielt werden?
 *
 * `unusedSeconds`: wie lange das Fenster schon zu ist. Bewusst nicht die
 * Leerlaufzeit des Systems - die meldet unter Wayland oft immer 0, und wer
 * nebenher etwas anderes tut, stoert ein Neustart im Tray nicht.
 */
function idleForUpdate({ windowVisible, busy, unusedSeconds, refreshAt, now }) {
  if (windowVisible || busy) return false;
  if (!(unusedSeconds >= UPDATE_IDLE_SECONDS)) return false;
  // Steht ein Refresh kurz bevor, erst den. Ist er schon faellig, laeuft er
  // entweder (busy) oder wartet aufs iPhone - das kann Tage dauern.
  if (refreshAt != null && refreshAt > now && refreshAt - now < UPDATE_REFRESH_MARGIN) return false;
  return true;
}

module.exports = {
  HOUR, DAY, STALE_AFTER, DEVICE_NAG_EVERY, UPDATE_IDLE_SECONDS,
  emptyMemory, normalizeMemory, plan, manualPlan, onRefreshResult, forgetBackoff,
  nextRefreshAt, nextExpiring, idleForUpdate,
};
