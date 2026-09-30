// Was das Backend (modstaller/server.py) liefert.

/** Wie das Geraet erreicht wird (modstaller/device/discovery.py). */
export type Transport = "usb" | "usbmux-net" | "wifi" | "remote";

export interface Device {
  name: string;
  udid: string;
  /** Die Version des Systems - iOS oder tvOS. */
  iosVersion: string;
  /** null: noch nicht gefragt (Geraet in der Liste, aber nicht ausgewaehlt). */
  developerMode: boolean | null;
  productType: string;
  /** "iPhone 16 Pro Max" statt "iPhone17,2". */
  model: string;
  formFactor: "home" | "notch" | "island" | "ipad" | "ipod" | "tv" | "vision";
  platform: "ios" | "tvos" | "xros";
  transport: Transport;
  /** WLAN ist fuer dieses Geraet in ModStaller eingeschaltet. */
  wifiEnabled: boolean;
  battery: { level: number; charging: boolean } | null;
}

export interface App {
  bundleId: string;
  originalBundleId: string;
  name: string;
  daysLeft: number;
  expiresAt: number;
  expiryText: string;
  urgent: boolean;
  sourceIpa: string;
  sourceMissing: boolean;
  teamId: string;
  /** Der Apple-Account, der sie signiert hat - leer bei alten Eintraegen. */
  adsid: string;
}

/** Ein angemeldeter Apple-Account. */
export interface Account {
  adsid: string;
  /** Leer bei Sitzungen aus Versionen vor der Mehr-Account-Unterstuetzung. */
  appleId: string;
  firstName: string;
  /** Apple-ID, sonst Vorname, sonst adsid. */
  label: string;
  /** Neue Installationen signieren mit diesem Account. */
  active: boolean;
}

/** Woher eine App auf dem iPhone stammt - aus ihrer Signatur abgeleitet. */
export type Origin = "store" | "testflight" | "developer" | "other";

/** Ein Eintrag aus "apps.overview": eigenes und fremdes nebeneinander. */
export interface SideloadedApp {
  bundleId: string;
  name: string;
  version: string;
  /** Liegt sie gerade auf dem iPhone? Sonst kennt ModStaller sie nur noch. */
  onDevice: boolean;
  /** Von ModStaller installiert - nur dann gibt es Quelle und Ablaufdatum. */
  managed: boolean;
  signer: string;
  teamId: string;
  origin: Origin;
  sideloaded: boolean;
  developerSigned: boolean;
  sourceIpa: string;
  sourceMissing: boolean;
  originalBundleId: string;
  appIdId: string;
  expiresAt: number | null;
  daysLeft: number | null;
  expiryText: string;
  urgent: boolean;
  installedAt: number | null;
}

export interface Status {
  /** Das ausgewaehlte Geraet - ausfuehrlich. */
  device: Device | null;
  /** Alle erreichbaren Geraete, Kabel zuerst. */
  devices: Device[];
  selectedUdid: string | null;
  deviceAttached: boolean;
  loggedIn: boolean;
  /** Vorname des Apple-Accounts fuer die Begruessung - leer, wenn unbekannt. */
  firstName: string;
  accounts: Account[];
  apps: App[];
  urgent: string[];
  urgentDays: number;
  error: string;
  /** Windows: Apple-Geraetedienst fehlt ("missing") oder ist gestoppt. */
  usbService?: "ok" | "missing" | "stopped";
}

export interface UsbSetupResult {
  method: "already" | "started" | "apple-devices" | "driver";
  message: string;
}

export interface FoundIpa {
  path: string;
  name: string;
  size: number;
  modified: number;
}

export interface IpaInfo {
  path: string;
  bundleId: string;
  name: string;
  version: string;
  minimumOs: string;
  /** Fuer iPhone/iPad/iPod, Apple TV oder Vision Pro. */
  platform: "ios" | "tvos" | "xros";
  /** UIDeviceFamily: 1 iPhone/iPod, 2 iPad, 3 Apple TV, 7 Vision Pro. */
  deviceFamilies: number[];
  extensions: string[];
  extensionDetails: ExtensionDetail[];
  hasWatch: boolean;
  /** Das Original-Icon als data:-URL - null, wenn es nur im Assets.car steckt. */
  icon: string | null;
  frameworks: string[];
  dylibs: string[];
  encrypted: boolean;
  size: number;
}

export interface ExtensionDetail {
  path: string;
  bundleId: string;
  name: string;
  /** NSExtensionPointIdentifier - was fuer eine Extension. */
  point: string;
  /** Traegt die ID der App als Praefix - nur dann laesst sie sich behalten. */
  movable: boolean;
}

/** Wie viele App-IDs diese Woche noch angelegt werden duerfen (modstaller/quota.py). */
export interface Quota {
  maximum: number | null;
  available: number | null;
  /** Unix-Zeit - nur gesetzt, wenn gerade keine frei ist (Schaetzung). */
  nextFreeAt: number | null;
  /** Wann die bekannten Anlagen im Fenster wieder frei werden. */
  returnsAt: number[];
}

/** App-Slots mit Free-Profil auf dem iPhone - null ohne iPhone. */
export interface Slots {
  max: number | null;
  used: number;
  apps: { bundleId: string; name: string }[];
}

export interface InstallPlan {
  teamId: string;
  teamName: string;
  isFree: boolean;
  defaultBundleId: string;
  mainId: string;
  spare: string | null;
  /** Die behaltenen Extensions - ohne eigene Wahl die Voreinstellung. */
  keep: string[];
  extensions: { path: string; identifier: string }[];
  newAppIds: string[];
  notes: string[];
  /** Reicht das Kontingent nicht: warum. */
  error: string | null;
  quota: Quota;
  spares: { identifier: string; appIdId: string; expiresAt: number | null }[];
  slots: Slots | null;
}

/** Was der Editor im Installieren-Screen geaendert hat. */
export interface InstallChoice {
  displayName?: string;
  bundleId?: string;
  /** PNG als data:-URL, 1024 x 1024. */
  icon?: string;
  extensions?: string[];
  spareAppId?: string;
  account?: string;
  /** Die IPA kam aus dem Store - fuer spaetere Update-Hinweise. */
  store?: StoreOrigin;
}

/** Woher eine IPA im Store stammt. */
export interface StoreOrigin {
  source: string;
  bundleId: string;
  version: string;
}

/** Ein Eintrag aus "store.list". */
export interface StoreApp {
  source: string;
  name: string;
  bundleId: string;
  version: string;
  developer: string;
  date: string;
  size: number;
  iconUrl: string;
  subtitle: string;
  category: string;
  minOs: string;
  tint: string;
  /** "jailbreak", "exploit", "store" - oder leer (modstaller/store/risk.py). */
  warning: "" | "jailbreak" | "exploit" | "store";
  /** In wie vielen Quellen es diese App gibt ("store.list"). */
  offers?: number;
}

/** Ein Angebot derselben App aus einer Quelle. */
export interface StoreOffer {
  source: string;
  version: string;
  size: number;
  date: string;
}

export interface StoreVersion {
  version: string;
  date: string;
  download_url: string;
  size: number;
  min_os: string;
  sha256: string;
  notes: string;
}

/** "store.app": alles fuer die Detailansicht. */
export interface StoreAppDetail extends Omit<StoreApp, "offers"> {
  description: string;
  screenshots: string[];
  versions: StoreVersion[];
  /** Alle Quellen mit dieser App, das beste Angebot zuerst. */
  offers: StoreOffer[];
}

export interface StoreList {
  total: number;
  items: StoreApp[];
  categories: string[];
}

export interface StoreSource {
  url: string;
  enabled: boolean;
  name: string;
  iconUrl: string;
  subtitle: string;
  apps: number;
  fetchedAt: number | null;
  error: string;
  /** Hinweis zur Quelle, z. B. "jailbreak": fuehrt auch Jailbreak-Tools. */
  notice: string;
}

/** Eine installierte Store-App mit neuerer Version in ihrer Quelle. */
export interface StoreUpdate {
  bundleId: string;
  name: string;
  installed: string;
  offered: string;
  source: string;
  storeBundleId: string;
  size: number;
}

export interface InstallOutcome {
  bundleId: string;
  name: string;
  transport: string;
  daysValid: number;
  strippedExtensions: boolean;
  keptExtensions: number;
  newAppIds: number;
  /** Beim Erneuern auf diese Store-Version aktualisiert - sonst leer. */
  updatedTo?: string;
}

export interface JitResult {
  summary: string;
  notes: string[];
  pid: number;
  preparedRegions: number;
  preparedBytes: number;
  detachedCleanly: boolean;
  /** False when the device needs no conversation - attaching once is enough. */
  txm: boolean;
}

export interface Team {
  teamId: string;
  name: string;
  type: string;
  isFree: boolean;
  description: string;
  devices: number;
  appIds: AppId[];
  /** Ob beim Lesen ein iPhone angesteckt war. Nur dann stimmt `inUse`. */
  usageKnown: boolean;
  maxAppIdsPerWeek: number | null;
  maxAppsPerDevice: number | null;
  quota: Quota;
  slots: Slots | null;
}

export interface AppId {
  appIdId: string;
  identifier: string;
  name: string;
  /** Gehoert zu einer App, die ModStaller installiert hat. */
  inUse: boolean;
  /** Free-Accounts: Unix-Zeit, zu der die App-ID ablaeuft. */
  expiresAt: number | null;
}

export interface Cert {
  certId: string;
  serial: string;
  name: string;
  machineId: string;
  expiresAt: string | null;
}

export interface Check {
  label: string;
  ok: boolean;
  detail: string;
  hint: string;
  kind: "problem" | "todo";
}

export interface DeviceInfo {
  udid: string;
  name: string;
  productType: string;
  iosVersion: string;
  build: string;
  developerMode: boolean;
  platform: "ios" | "tvos" | "xros";
  transport: Transport;
}

export interface DeviceApp {
  bundleId: string;
  name: string;
  version: string;
}

export interface DeviceCheck {
  id: string;
  label: string;
  state: "ok" | "warn" | "bad" | "info" | "na";
  detail: string;
  fix: string | null;
  fix_label: string;
  manual: string;
}

export interface FixResult {
  message: string;
  manual: string;
}

/** Ein Eintrag im Protokoll (modstaller/logbook.py). */
export interface LogEntry {
  id: number;
  /** Sekunden seit 1970, wie Pythons time.time(). */
  ts: number;
  level: "debug" | "info" | "success" | "warn" | "error";
  source: "install" | "refresh" | "jit" | "apps" | "device" | "account" | "system";
  message: string;
  /** ID der Anfrage, zu der er gehoert - null bei Ereignissen. */
  job: number | null;
}

export interface BackendExit {
  code: number | null;
  reason: string;
  stderr: string;
}

/** Was der Hauptprozess ueber das Backend weiss - auch rueckwirkend. */
export type BackendState =
  | { state: "starting" }
  | { state: "running"; pid?: number }
  | ({ state: "down" } & BackendExit);

export interface UpdateState {
  state: "unsupported" | "checking" | "none" | "available" | "downloading" | "ready" | "error";
  current?: string;
  version?: string;
  notes?: string;
  percent?: number;
  message?: string;
  /** Beta-Kanal an: Betas (-beta.x) werden mit angeboten. */
  beta?: boolean;
  /** Die angebotene Version ist eine Beta. */
  prerelease?: boolean;
  /** Von einem Paketmanager installiert ("aur") - der aktualisiert. */
  managedBy?: string;
}

/** Hintergrundbetrieb (electron/daemon-prefs.cjs). */
export interface DaemonPrefs {
  autostart: boolean;
  closeToTray: boolean;
  remind: boolean;
  remindDaysBefore: number;
  autoRefresh: boolean;
  refreshHoursBefore: number;
  autoUpdate: boolean;
  /** Store-Apps beim Erneuern auf die neueste Version ihrer Quelle bringen. */
  storeAutoUpdate: boolean;
  language: string | null;
  /** Kann diese Kopie mit dem System starten (nicht in der Entwicklung,
   *  nicht aus einer entpackten AppImage)? */
  autostartAvailable: boolean;
  trayAvailable: boolean;
}

/** Was der Hintergrund gerade tut. */
export interface DaemonState {
  refreshing: { bundleId: string; name: string } | null;
}

/** Ein Apple TV, das gerade den Koppel-Bildschirm zeigt ("pair.browse"). */
export interface PairableTv {
  name: string;
  identifier: string;
  host: string;
  port: number;
  model: string;
  /** "appletv", "vision" - oder leer, wenn das Geraet es nicht sagt. */
  kind: "appletv" | "vision" | "";
}

/** Linux-Setup: was schon installiert ist und wohin. */
export interface SetupInfo {
  version: string;
  installed: string | null;
  update: boolean;
  launchAfter: boolean;
  paths: { app: string; launcher: string; cli: string; desktop: string };
  binOnPath: boolean;
}

export interface SetupResult {
  version: string;
  cli: boolean;
  binOnPath: boolean;
  files: string[];
}

export interface SetupProgress {
  step: "copy" | "activate" | "done";
  percent: number;
}

declare global {
  interface Window {
    /** Nur im Linux-Setup vorhanden (preload.cjs). */
    setup?: {
      autoUpdate: boolean;
      info(): Promise<SetupInfo>;
      install(choice: { language?: string; desktopShortcut?: boolean }): Promise<SetupResult>;
      uninstall(choice: { purge: boolean }): Promise<void>;
      launch(): Promise<void>;
      quit(): Promise<void>;
      onProgress(cb: (p: SetupProgress) => void): () => void;
    };
    daemon: {
      getPrefs(): Promise<DaemonPrefs>;
      setPrefs(partial: Partial<DaemonPrefs>): Promise<DaemonPrefs>;
      getState(): Promise<DaemonState>;
      onState(cb: (s: DaemonState) => void): () => void;
    };
    updates: {
      get(): Promise<UpdateState>;
      onState(cb: (s: UpdateState) => void): () => void;
      check(): Promise<void>;
      download(): Promise<void>;
      install(): Promise<void>;
      getBeta(): Promise<boolean>;
      setBeta(on: boolean): Promise<void>;
    };
    backend: {
      platform: string;
      /** Startsprache aus dem Setup - nur beim ersten Start danach. */
      initialLanguage: string | null;
      send(msg: unknown): void;
      onMessage(cb: (msg: any) => void): () => void;
      onExit(cb: (info: BackendExit) => void): () => void;
      getState(): Promise<BackendState>;
      logPath(): Promise<string>;
      showFile(path: string): Promise<void>;
      restart(): void;
      pickIpa(): Promise<string | null>;
      pathForFile(file: File): string;
    };
  }
}
