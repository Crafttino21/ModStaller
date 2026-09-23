export function mb(bytes: number): string {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.round(bytes / 1e6)} MB`;
}

export function days(d: number): string {
  if (d < 0) return "abgelaufen";
  if (d < 1) {
    const h = Math.max(1, Math.round(d * 24));
    return `noch ${h} ${h === 1 ? "Stunde" : "Stunden"}`;
  }
  const n = Math.floor(d);
  return `noch ${n} ${n === 1 ? "Tag" : "Tage"}`;
}

export function date(ts: number): string {
  return new Date(ts * 1000).toLocaleString("de-DE", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

export function relative(ts: number): string {
  const diff = Date.now() / 1000 - ts;
  if (diff < 3600) return "gerade eben";
  if (diff < 86400) return `vor ${Math.round(diff / 3600)} Std.`;
  const d = Math.round(diff / 86400);
  return d === 1 ? "gestern" : `vor ${d} Tagen`;
}

/** Ampel nach Restlaufzeit: gleiche Schwelle wie das Backend. */
export function tone(daysLeft: number, urgentDays: number): "ok" | "warn" | "bad" {
  if (daysLeft < 0) return "bad";
  return daysLeft <= urgentDays ? "warn" : "ok";
}
