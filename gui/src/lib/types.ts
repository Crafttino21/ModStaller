// Was das Backend (modstaller/server.py) liefert.

export interface Device {
  name: string;
  udid: string;
  iosVersion: string;
  developerMode: boolean;
  productType: string;
  /** "iPhone 16 Pro Max" statt "iPhone17,2". */
  model: string;
  formFactor: "home" | "notch" | "island" | "ipad";
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
}

export interface Status {
  device: Device | null;
  deviceAttached: boolean;
  loggedIn: boolean;
  apps: App[];
  urgent: string[];
  urgentDays: number;
  error: string;
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
  extensions: string[];
  frameworks: string[];
  dylibs: string[];
  encrypted: boolean;
  size: number;
}

export interface InstallOutcome {
  bundleId: string;
  name: string;
  transport: string;
  daysValid: number;
  strippedExtensions: boolean;
}

export interface JitResult {
  summary: string;
  notes: string[];
  pid: number;
  preparedRegions: number;
  preparedBytes: number;
  detachedCleanly: boolean;
}

export interface Team {
  teamId: string;
  name: string;
  type: string;
  isFree: boolean;
  description: string;
  devices: number;
  appIds: string[];
  maxAppIdsPerWeek: number | null;
  maxAppsPerDevice: number | null;
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

export interface BackendExit {
  code: number | null;
  reason: string;
  stderr: string;
}

export interface UpdateState {
  state: "unsupported" | "checking" | "none" | "available" | "downloading" | "ready" | "error";
  current?: string;
  version?: string;
  notes?: string;
  percent?: number;
  message?: string;
}

declare global {
  interface Window {
    updates: {
      get(): Promise<UpdateState>;
      onState(cb: (s: UpdateState) => void): () => void;
      check(): Promise<void>;
      download(): Promise<void>;
      install(): Promise<void>;
    };
    backend: {
      platform: string;
      send(msg: unknown): void;
      onMessage(cb: (msg: any) => void): () => void;
      onExit(cb: (info: BackendExit) => void): () => void;
      restart(): void;
      pickIpa(): Promise<string | null>;
      pathForFile(file: File): string;
    };
  }
}
