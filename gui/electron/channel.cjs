// Update-Kanal: nur stabile Versionen oder auch Betas (-beta.x).
//
// Die Wahl liegt im Hauptprozess, nicht im localStorage der Oberflaeche: der
// erste Update-Check laeuft, bevor die Seite geladen ist. Eigene Datei, damit
// sich die Logik ohne Electron pruefen laesst.

const fs = require("node:fs");

/** Hat die Version einen Vorab-Anhang wie "-beta.3"? */
function isPrerelease(version) {
  return /^\d+\.\d+\.\d+-/.test(String(version ?? ""));
}

/**
 * Die gespeicherte Wahl - oder, ohne Datei, das bisherige Verhalten:
 * wer eine Beta laeuft, bleibt im Beta-Kanal, alle anderen bekommen nur
 * stabile Versionen.
 */
function readPrefs(file, currentVersion) {
  try {
    const raw = JSON.parse(fs.readFileSync(file, "utf8"));
    if (typeof raw?.beta === "boolean") return { beta: raw.beta };
  } catch {
    // fehlt oder kaputt - dann der Standard
  }
  return { beta: isPrerelease(currentVersion) };
}

function writePrefs(file, prefs) {
  fs.writeFileSync(file, JSON.stringify({ beta: Boolean(prefs.beta) }, null, 2));
}

/**
 * Die Einstellungen fuer electron-updater. allowPrerelease muss immer
 * ausdruecklich gesetzt werden: von sich aus leitet die Bibliothek es aus
 * der laufenden Version ab. Nie ein Downgrade - wer den Beta-Kanal verlaesst,
 * behaelt seine Beta bis zur naechsten neueren stabilen Version.
 */
function updaterFlags({ beta }) {
  return { allowPrerelease: Boolean(beta), allowDowngrade: false };
}

module.exports = { isPrerelease, readPrefs, writePrefs, updaterFlags };
