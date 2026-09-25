// Tests fuer plainNotes - ohne Electron, mit dem Testlaeufer von Node.
//
//     cd gui && npm test
//
// Die ersten beiden Faelle sind die, die CodeQL an der alten Fassung gemeldet
// hat. Sie stehen zuerst, weil sie der Grund fuer diese Datei sind.

"use strict";

const test = require("node:test");
const assert = require("node:assert");

const { plainNotes, decodeEntities, stripTags } = require("./notes.cjs");

test("Entities werden nur einmal aufgeloest", () => {
  // Die alte Fassung ersetzte erst &amp;, dann &lt; - aus dem Text "&lt;"
  // wurde so ein echtes "<". Richtig ist: der Text bleibt Text.
  assert.equal(plainNotes("&amp;lt;script&amp;gt;"), "&lt;script&gt;");
  assert.equal(decodeEntities("&amp;amp;"), "&amp;");
});

test("verschachtelte Tags bleiben nicht als Tag zurueck", () => {
  // Ein einzelner Durchlauf macht aus "<scr<b>ipt>" ein "<script>".
  assert.equal(stripTags("<scr<b>ipt>alert(1)</scr</b>ipt>"), "alert(1)");
  assert.equal(plainNotes("<scr<b>ipt>x</scr<b>ipt>"), "x");
});

test("gewoehnliche Notes werden lesbarer Text", () => {
  assert.equal(
    plainNotes("<p>Erste Zeile</p><p>Zweite <b>fett</b></p>"),
    "Erste Zeile\nZweite fett",
  );
  assert.equal(plainNotes("a<br>b<br/>c"), "a\nb\nc");
  assert.equal(plainNotes("Vorher<!-- versteckt -->Nachher"), "VorherNachher");
});

test("Entities werden aufgeloest, auch numerische", () => {
  assert.equal(plainNotes("Tom &amp; Jerry"), "Tom & Jerry");
  assert.equal(plainNotes("&#65;&#x42;"), "AB");
  // Unbekanntes und Unsinniges bleibt stehen, statt zu verschwinden.
  assert.equal(plainNotes("&nichtsda; &#0; &#xD800;"), "&nichtsda; &#0; &#xD800;");
});

test("ein einzelnes Kleiner-als ist kein Tag", () => {
  assert.equal(plainNotes("a < b und c > d"), "a < b und c > d");
});

test("Leerzeilen werden zusammengefasst und Raender beschnitten", () => {
  // trim() raeumt nur die Raender - Leerzeichen mitten im Text bleiben.
  assert.equal(plainNotes("\n\n\n  Text  \n\n\n\n  Mehr \n\n"), "Text  \n\n  Mehr");
});

test("die Formen von electron-updater kommen alle an", () => {
  assert.equal(plainNotes(null), "");
  assert.equal(plainNotes(undefined), "");
  assert.equal(plainNotes("<p>schlicht</p>"), "schlicht");
  assert.equal(plainNotes([{ version: "1.0", note: "<p>eins</p>" },
                           { version: "1.1", note: "<p>zwei</p>" }]),
               "eins\n\nzwei");
  assert.equal(plainNotes(["<p>eins</p>", "<p>zwei</p>"]), "eins\n\nzwei");
});
