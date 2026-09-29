// Einstellungen fuer den Betrieb im Hintergrund: Tray, Autostart,
// Erinnerungen, automatischer Refresh und automatische Updates.
//
// Wie channel.cjs im Hauptprozess, nicht im localStorage der Oberflaeche:
// mit --background gibt es gar keine Seite, die sie lesen koennte. Eigene
// Datei, damit sich die Logik ohne Electron pruefen laesst.

const fs = require("node:fs");

const DEFAULTS = Object.freeze({
  autostart: true,
  closeToTray: true,
  remind: true,
  remindDaysBefore: 3,
  autoRefresh: true,
  refreshHoursBefore: 24,
  autoUpdate: true,
  // Sprache der Benachrichtigungen - die Oberflaeche meldet sie (siehe
  // daemon-i18n.cjs). null: noch nie gemeldet, dann Englisch.
  language: null,
});

/** Grenzen fuer die Zahlen. Mehr als 6 Tage Vorlauf erinnert bei 7 Tage
 *  gueltigen Profilen gleich nach dem Refresh wieder. */
const LIMITS = Object.freeze({
  remindDaysBefore: [1, 6],
  refreshHoursBefore: [6, 72],
});

function clamp(value, [lo, hi], fallback) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(hi, Math.max(lo, Math.round(n)));
}

/** Nur bekannte Schluessel, jeder mit dem richtigen Typ - der Rest faellt auf
 *  den Standard (oder den bisherigen Wert) zurueck. */
function sanitize(raw, base = DEFAULTS) {
  const out = { ...base };
  if (!raw || typeof raw !== "object") return out;
  for (const key of ["autostart", "closeToTray", "remind", "autoRefresh", "autoUpdate"]) {
    if (typeof raw[key] === "boolean") out[key] = raw[key];
  }
  for (const [key, range] of Object.entries(LIMITS)) {
    if (key in raw) out[key] = clamp(raw[key], range, base[key]);
  }
  if (typeof raw.language === "string" && /^[a-zA-Z-]{2,10}$/.test(raw.language)) {
    out.language = raw.language;
  }
  return out;
}

function readPrefs(file) {
  try {
    return sanitize(JSON.parse(fs.readFileSync(file, "utf8")));
  } catch {
    return { ...DEFAULTS };   // fehlt oder kaputt - dann der Standard
  }
}

/** Uebernimmt `partial` in die gespeicherten Einstellungen und gibt das
 *  Ergebnis zurueck. */
function writePrefs(file, partial) {
  const next = sanitize(partial, readPrefs(file));
  fs.writeFileSync(file, JSON.stringify(next, null, 2));
  return next;
}

module.exports = { DEFAULTS, LIMITS, sanitize, readPrefs, writePrefs };
