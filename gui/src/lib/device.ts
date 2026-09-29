// Wie ein Geraet heisst und wie es verbunden ist - fuer alle Ansichten gleich.

import { t } from "./i18n.svelte";
import type { Device } from "./types";

type Kindish = Pick<Device, "platform" | "formFactor"> | null | undefined;

/** "iPhone", "iPad", "iPod touch", "Apple TV" oder "Apple Vision Pro". */
export function deviceKind(d: Kindish): string {
  if (d?.platform === "tvos") return "Apple TV";
  if (d?.platform === "xros") return "Apple Vision Pro";
  if (d?.formFactor === "ipad") return "iPad";
  if (d?.formFactor === "ipod") return "iPod touch";
  return "iPhone";
}

/** "iOS", "iPadOS", "tvOS" oder "visionOS". */
export function osName(d: Partial<Pick<Device, "platform" | "formFactor">> | null | undefined): string {
  if (d?.platform === "tvos") return "tvOS";
  if (d?.platform === "xros") return "visionOS";
  return d?.formFactor === "ipad" ? "iPadOS" : "iOS";
}

/** Apple TV und Vision Pro: nur uebers Netz, per Kopplung - ohne Kabel,
 *  ohne WLAN-Schalter und (noch) ohne JIT. */
export function networkOnly(d: Pick<Device, "platform"> | null | undefined): boolean {
  return d?.platform === "tvos" || d?.platform === "xros";
}

/** JIT gibt es nur fuer iPhone, iPad und iPod touch. */
export function jitAvailable(d: Pick<Device, "platform"> | null | undefined): boolean {
  return !d || d.platform === "ios";
}

/** Ueber das Netz statt ueber das Kabel? */
export function overNetwork(d: Pick<Device, "transport"> | null | undefined): boolean {
  return !!d && d.transport !== "usb";
}

/** "USB" oder "WLAN". */
export function transportLabel(d: Pick<Device, "transport"> | null | undefined): string {
  return overNetwork(d) ? t("Wi-Fi") : "USB";
}

/** Hoehe des Mockups: breite Geraete (TV, Vision Pro) flacher zeichnen. */
export function mockupHeight(d: Pick<Device, "formFactor"> | null | undefined, tall: number): number {
  return d?.formFactor === "tv" || d?.formFactor === "vision" ? Math.round(tall * 0.7) : tall;
}

/** Warum diese IPA nicht auf dieses Geraet passt - oder null. Dieselben Regeln
 *  wie im Backend (pipeline.incompatibility), damit der Knopf gar nicht erst
 *  anbietet, was Apple-Kontingent kostet und dann scheitert. */
export function incompatibility(
  ipa: { platform: string; deviceFamilies?: number[] },
  d: Pick<Device, "platform" | "formFactor">,
): string | null {
  if (ipa.platform !== d.platform) {
    if (d.platform === "xros" && ipa.platform === "ios") return null;   // "Designed for iPad"
    if (ipa.platform === "tvos") return t("This IPA is an Apple TV app – pick the Apple TV as the device.");
    if (ipa.platform === "xros") return t("This IPA is an Apple Vision Pro app – pick the Vision Pro as the device.");
    return t("This IPA is for iPhone and iPad – an Apple TV needs the app's tvOS version.");
  }
  const families = ipa.deviceFamilies ?? [];
  if (d.platform === "ios" && families.length && families.every((f) => f === 2) && d.formFactor !== "ipad")
    return t("This app is made for iPad only and does not start on an {kind}.", { kind: deviceKind(d) });
  return null;
}
