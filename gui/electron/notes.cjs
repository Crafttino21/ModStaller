// Release-Notes von GitHub in reinen Text verwandeln.
//
// Eigene Datei, weil hier zwei Fehlerklassen lauern, die man nur sieht, wenn
// man sie hinschreibt - und die sich so ohne Electron testen lassen
// (notes.test.cjs). Beide hat CodeQL in der alten, einzeiligen Fassung
// gefunden: doppeltes Aufloesen von Entities und unvollstaendiges Entfernen
// von Tags.
//
// Heute landet das Ergebnis in einer Svelte-Textinterpolation, die selbst
// maskiert - ein Loch ist es also nicht. Aber es ist die Sorte Funktion, die
// eines Tages hinter {@html} steht, und falsch war sie ohnehin: aus dem
// harmlosen "&amp;lt;" wurde ein "<".

"use strict";

/** Die Entities, die in Release-Notes ueberhaupt vorkommen. */
const ENTITIES = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: "\"",
  apos: "'",
  nbsp: " ",
};

/**
 * Entities in *einem* Durchgang aufloesen.
 *
 * Nacheinander waere falsch: wer erst `&amp;` ersetzt, macht aus dem
 * harmlosen `&amp;lt;` ein `&lt;` und im naechsten Schritt ein `<` - aus Text
 * wird Markup. Ein einziger Durchgang setzt hinter jedem Treffer fort und
 * kann sein eigenes Ergebnis nicht noch einmal lesen.
 */
function decodeEntities(text) {
  return text.replace(/&(#\d{1,7}|#x[0-9a-f]{1,6}|[a-z]+);/gi, (whole, name) => {
    if (name[0] !== "#") {
      const known = ENTITIES[name.toLowerCase()];
      return known === undefined ? whole : known;
    }
    const code = name[1] === "x" || name[1] === "X"
      ? parseInt(name.slice(2), 16)
      : parseInt(name.slice(1), 10);
    if (!Number.isInteger(code) || code <= 0 || code > 0x10ffff) return whole;
    // Einzelne Surrogat-Haelften sind kein gueltiger Codepoint.
    if (code >= 0xd800 && code <= 0xdfff) return whole;
    return String.fromCodePoint(code);
  });
}

/**
 * Tags entfernen, bis sich nichts mehr aendert.
 *
 * Ein Durchgang genuegt nicht: aus `<scr<b>ipt>` wird durch das Entfernen von
 * `<b>` erst ein `<script>`. Das Muster verbietet `<` im Inneren, damit genau
 * diese Schachtelung stehen bleibt und der naechste Durchgang sie sieht.
 * Jeder Durchgang verkuerzt den Text, also endet die Schleife.
 *
 * Nach `<` muss ein Buchstabe folgen (oder `/` und ein Buchstabe). Sonst
 * frisst die Funktion Prosa: "a < b und c > d" saehe sonst wie ein Tag aus.
 */
function stripTags(text) {
  let before;
  do {
    before = text;
    text = text.replace(/<|>/g, "");
  } while (text !== before);
  return text;
}

/**
 * Release-Notes als reiner Text.
 *
 * Die Reihenfolge ist wesentlich: erst Struktur in Zeilenumbrueche, dann Tags
 * weg, erst danach die Entities. Wer frueher dekodiert, bastelt sich aus
 * `&lt;b&gt;` wieder ein Tag, das der Tag-Schritt nicht mehr zu sehen bekommt.
 *
 * electron-updater liefert entweder einen String oder eine Liste von
 * `{ version, note }` - beides kommt hier an.
 */
function plainNotes(notes) {
  const raw = Array.isArray(notes)
    ? notes.map((n) => (typeof n === "string" ? n : n?.note ?? "")).join("\n\n")
    : notes ?? "";
  const text = String(raw)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|li|h\d)>/gi, "\n");
  return decodeEntities(stripTags(text)).replace(/\n{3,}/g, "\n\n").trim();
}

module.exports = { plainNotes, decodeEntities, stripTags };
