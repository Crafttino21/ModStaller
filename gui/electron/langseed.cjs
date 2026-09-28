// Startsprache aus dem Setup.
//
// Das Setup (NSIS unter Windows, der Linux-Assistent) kann nicht in den
// localStorage der Oberflaeche schreiben. Es legt stattdessen language.json in
// den userData-Ordner. Der Hauptprozess nimmt sie beim Start genau einmal an
// sich und loescht sie: eine Neuinstallation mit anderer Wahl gewinnt, die
// spaetere Wahl in den Einstellungen bleibt danach unangetastet.
//
// Eigene Datei, damit sich das ohne Electron pruefen laesst.

const fs = require("node:fs");
const path = require("node:path");

/** Dateiname im userData-Ordner - build/installer.nsh schreibt denselben. */
const SEED_FILE = "language.json";

/** Sieht aus wie ein Sprachcode ("de", "pt-BR")? Welche Sprache es wirklich
 *  gibt, entscheidet die Oberflaeche (resolve in src/lib/i18n.svelte.ts). */
function isLanguageCode(code) {
  return typeof code === "string" && /^[a-z]{2,3}([-_][A-Za-z]{2,4})?$/.test(code);
}

/** Die hinterlegte Sprache - oder null. Die Datei ist danach weg, auch wenn
 *  sie kaputt war: sonst wuerde sie bei jedem Start erneut gelesen. */
function takeSeed(file) {
  let code = null;
  try {
    const raw = JSON.parse(fs.readFileSync(file, "utf8"));
    if (isLanguageCode(raw?.language)) code = raw.language;
  } catch {
    // fehlt oder kaputt
  }
  try {
    fs.rmSync(file, { force: true });
  } catch {
    // nicht loeschbar: dann gilt sie eben noch einmal
  }
  return code;
}

/** Legt die Startsprache fuer den naechsten Start ab (Linux-Assistent). */
function writeSeed(file, code) {
  if (!isLanguageCode(code)) return false;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify({ language: code }));
  return true;
}

/** Das Argument, mit dem die Sprache ins Fenster kommt (siehe preload.cjs). */
const ARG = "--ms-lang=";

module.exports = { SEED_FILE, ARG, isLanguageCode, takeSeed, writeSeed };
