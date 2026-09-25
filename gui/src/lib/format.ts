import { locale, t, tn } from "./i18n.svelte";

export function mb(bytes: number): string {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.round(bytes / 1e6)} MB`;
}

/** Nur der Dateiname - Pfade sind zu lang fuer eine Zeile. Beide Trenner,
 *  weil die Quelle unter Windows wie unter Linux aufgezeichnet wird. */
export function basename(path: string): string {
  const cut = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return cut < 0 ? path : path.slice(cut + 1);
}

export function days(d: number): string {
  if (d < 0) return t("expired");
  if (d < 1) {
    const h = Math.max(1, Math.round(d * 24));
    return tn("{count} hour left", "{count} hours left", h);
  }
  const n = Math.floor(d);
  return tn("{count} day left", "{count} days left", n);
}

export function date(ts: number): string {
  return new Date(ts * 1000).toLocaleString(locale(), {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

export function relative(ts: number): string {
  const diff = Date.now() / 1000 - ts;
  if (diff < 3600) return t("just now");
  if (diff < 86400) return t("{count} h ago", { count: Math.round(diff / 3600) });
  const d = Math.round(diff / 86400);
  return d === 1 ? t("yesterday") : t("{count} days ago", { count: d });
}

/** Ampel nach Restlaufzeit: gleiche Schwelle wie das Backend. */
export function tone(daysLeft: number, urgentDays: number): "ok" | "warn" | "bad" {
  if (daysLeft < 0) return "bad";
  return daysLeft <= urgentDays ? "warn" : "ok";
}
