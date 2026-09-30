// Was der Store zu einer App sagt, die Vorsicht verdient (modstaller/store/risk.py).

import { t } from "./i18n.svelte";

export type StoreWarning = "" | "jailbreak" | "exploit" | "store";

/** Kurzes Etikett fuer die Karte. */
export function warningLabel(w: StoreWarning): string {
  if (w === "jailbreak") return t("Jailbreak tool");
  if (w === "exploit") return t("Exploit");
  if (w === "store") return t("Third-party store");
  return "";
}

/** Der ausfuehrliche Hinweis im Detail und vor der Installation. */
export function warningText(w: StoreWarning): string {
  if (w === "jailbreak")
    return t("This is a jailbreak tool. It attacks the system with an exploit - a failed run can mean a boot loop, a restore and lost data, and it weakens the device's security. Only install it if you know exactly what you are doing.");
  if (w === "exploit")
    return t("This app changes the system through an exploit. That can go wrong and leave the device unstable - only install it if you know what it does.");
  if (w === "store")
    return t("This app installs apps from another store, many of them cracked. ModStaller cannot check what comes from there.");
  return "";
}
