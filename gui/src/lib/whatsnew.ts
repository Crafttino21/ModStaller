// Was eine Version Neues bringt - fuer das Popup nach einem Update.
//
// Die Eintraege stehen in whatsnew.json, einer je X.Y.Z. Die Texte sind
// englische Quelltexte und laufen erst beim Anzeigen durch t() - uebersetzt
// wird in locale/*.ts wie alles andere. Vorabversionen (1.4.0-rc.2) zeigen
// den Eintrag ihrer Version (1.4.0), und der kommt nur einmal: wer ihn mit
// rc.2 gesehen hat, bekommt ihn mit 1.4.0 nicht noch einmal.
//
// packaging/check-version.py verweigert eine Release ohne Eintrag - so
// bringt jedes Update sein Popup mit.

import data from "./whatsnew.json";

export interface Release {
  version: string;
  /** Steht hervorgehoben ganz oben - fuer das, was jeder wissen sollte. */
  highlight?: string;
  items: string[];
}

export const RELEASES: Release[] = data;

const SEEN_KEY = "modstaller.whatsNewSeen";

/** "1.4.0-rc.3" -> [1, 4, 0]; null, wenn es keine Versionsnummer ist ("dev"). */
function core(version: string): number[] | null {
  const m = /^(\d+)\.(\d+)\.(\d+)/.exec(version);
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

function compare(a: number[], b: number[]): number {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

/** Die Eintraege bis einschliesslich ``current``, neueste zuerst. */
export function releasesUpTo(current: string): Release[] {
  const top = core(current);
  if (!top) return [];
  return RELEASES
    .filter((r) => { const v = core(r.version); return v !== null && compare(v, top) <= 0; })
    .sort((a, b) => compare(core(b.version)!, core(a.version)!));
}

/**
 * Was seit ``seen`` (der Version, mit der das Popup zuletzt zu war)
 * dazugekommen ist. Ohne ``seen`` nur der neueste Eintrag - wer von einer
 * Version vor diesem Popup kommt, soll nicht die ganze Geschichte lesen.
 */
export function unseen(current: string, seen: string | null): Release[] {
  const list = releasesUpTo(current);
  const last = seen === null ? null : core(seen);
  if (last === null) return list.slice(0, 1);
  return list.filter((r) => compare(core(r.version)!, last) > 0);
}

export function readSeen(): string | null {
  try {
    return localStorage.getItem(SEEN_KEY);
  } catch {
    return null;
  }
}

export function markSeen(version: string) {
  try {
    localStorage.setItem(SEEN_KEY, version);
  } catch {
    // Nicht speicherbar: dann kommt das Popup beim naechsten Start noch einmal.
  }
}
