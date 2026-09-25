// Uebersetzung der Oberflaeche.
//
// Wie im Backend ist die Quellsprache Englisch, und der englische Satz *ist*
// der Schluessel. Man liest an der Fundstelle, was dort steht, und eine
// fehlende Uebersetzung faellt auf Englisch zurueck statt auf "apps.title".
//
//     {t("Apps")}
//     {t("{count} apps", { count: n })}
//
// Platzhalter sind benannt, nie positionell: in anderen Sprachen steht die
// Reihenfolge der Satzteile anders.

import de from "./locale/de";
import es from "./locale/es";
import fr from "./locale/fr";
import it from "./locale/it";
import nl from "./locale/nl";
import ptBR from "./locale/pt-BR";

export type Dict = Record<string, string>;

/** Die Quellsprache braucht keinen Katalog. */
export const SOURCE = "en";

/** Was in der Sprachauswahl steht - jeweils im eigenen Namen der Sprache. */
export const LANGUAGES: { code: string; name: string }[] = [
  { code: "en", name: "English" },
  { code: "de", name: "Deutsch" },
  { code: "fr", name: "Français" },
  { code: "es", name: "Español" },
  { code: "it", name: "Italiano" },
  { code: "pt-BR", name: "Português (Brasil)" },
  { code: "nl", name: "Nederlands" },
];

const CATALOGS: Record<string, Dict> = { de, fr, es, it, "pt-BR": ptBR, nl };

const STORAGE_KEY = "modstaller.language";

/** Die erste mitgelieferte Sprache, die zu `wanted` passt - sonst Englisch.
 *
 *  Ein Regionszusatz zaehlt nur, wenn wir ihn wirklich haben (`pt-BR`);
 *  sonst entscheidet die Sprache allein, damit `de-AT` bei Deutsch landet. */
export function resolve(wanted: string): string {
  const want = (wanted || "").replace("_", "-").trim().toLowerCase();
  if (!want) return SOURCE;
  const exact = LANGUAGES.find((l) => l.code.toLowerCase() === want);
  if (exact) return exact.code;
  const base = want.split("-")[0];
  const loose = LANGUAGES.find((l) => l.code.toLowerCase().split("-")[0] === base);
  return loose ? loose.code : SOURCE;
}

/** Ohne eigene Wahl: Englisch.
 *
 *  Bewusst nicht die Systemsprache. Wer ModStaller zum ersten Mal startet,
 *  soll dieselbe Oberflaeche sehen wie in jeder Anleitung und jedem
 *  Fehlerbericht; die eigene Sprache ist zwei Klicks entfernt und bleibt
 *  dann gespeichert. */
function initial(): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return resolve(saved);
  } catch {
    // Privates Fenster oder gesperrter Speicher - dann eben Englisch.
  }
  return SOURCE;
}

/** Die aktuelle Sprache. Alles, was `t()` benutzt, haengt daran. */
let current = $state(initial());

export function locale(): string {
  return current;
}

export function setLocale(code: string): string {
  current = resolve(code);
  try {
    localStorage.setItem(STORAGE_KEY, current);
  } catch {
    // Nicht speicherbar: gilt dann nur fuer diese Sitzung.
  }
  document.documentElement.lang = current;
  return current;
}

/** Der uebersetzte Satz, mit eingesetzten Platzhaltern. */
export function t(text: string, params?: Record<string, string | number>): string {
  const out = (CATALOGS[current]?.[text] || text);
  if (!params) return out;
  return out.replace(/\{(\w+)\}/g, (whole, key) =>
    key in params ? String(params[key]) : whole);
}

/** Ein- oder Mehrzahl. `count` steht als `{count}` zur Verfuegung.
 *
 *  Bewusst nur zwei Formen: mehr braucht keine der mitgelieferten Sprachen. */
export function tn(singular: string, plural: string, count: number,
                   params?: Record<string, string | number>): string {
  return t(count === 1 ? singular : plural, { count, ...params });
}
