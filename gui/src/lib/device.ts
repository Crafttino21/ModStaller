// Wie ein Geraet heisst und wie es verbunden ist - fuer alle Ansichten gleich.

import { t } from "./i18n.svelte";
import type { Device } from "./types";

/** "Apple TV", "iPad" oder "iPhone". */
export function deviceKind(d: Pick<Device, "platform" | "formFactor"> | null | undefined): string {
  if (d?.platform === "tvos") return "Apple TV";
  if (d?.formFactor === "ipad") return "iPad";
  return "iPhone";
}

/** "tvOS" oder "iOS". */
export function osName(d: Pick<Device, "platform"> | null | undefined): string {
  return d?.platform === "tvos" ? "tvOS" : "iOS";
}

/** Ueber das Netz statt ueber das Kabel? */
export function overNetwork(d: Pick<Device, "transport"> | null | undefined): boolean {
  return !!d && d.transport !== "usb";
}

/** "USB" oder "WLAN". */
export function transportLabel(d: Pick<Device, "transport"> | null | undefined): string {
  return overNetwork(d) ? t("Wi-Fi") : "USB";
}
