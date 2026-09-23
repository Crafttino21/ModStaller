// JSON-RPC 2.0 gegen `modstaller serve`. Der Electron-Hauptprozess reicht
// nur Zeilen durch - IDs, Antworten und Rueckfragen verwaltet dieser Client.

export const CANCELLED = -32800;

export class RpcError extends Error {
  constructor(public code: number, message: string) {
    super(message);
  }
  get cancelled() {
    return this.code === CANCELLED;
  }
}

export interface CallHooks {
  onLog?: (text: string) => void;
  onProgress?: (pct: number) => void;
}

interface Pending extends CallHooks {
  resolve: (v: any) => void;
  reject: (e: Error) => void;
}

type ServerRequestHandler = (params: any) => Promise<unknown>;

let nextId = 1;
const pending = new Map<number, Pending>();
const handlers = new Map<string, ServerRequestHandler>();
const readyListeners = new Set<() => void>();

window.backend.onMessage((msg) => {
  // Rueckfrage des Servers (z. B. der 2FA-Code).
  if (msg.method && msg.id != null) {
    const h = handlers.get(msg.method);
    const reply = (body: object) =>
      window.backend.send({ jsonrpc: "2.0", id: msg.id, ...body });
    if (!h) {
      reply({ error: { code: -32601, message: `Unbekannt: ${msg.method}` } });
      return;
    }
    h(msg.params).then(
      (result) => reply({ result }),
      (err) => reply({ error: { code: -32000, message: String(err?.message ?? err) } }),
    );
    return;
  }

  if (msg.method) {
    const p = msg.params ?? {};
    if (msg.method === "ready") readyListeners.forEach((f) => f());
    else if (msg.method === "log") pending.get(p.job)?.onLog?.(p.text);
    else if (msg.method === "progress") pending.get(p.job)?.onProgress?.(p.pct);
    return;
  }

  const p = pending.get(msg.id);
  if (!p) return;
  pending.delete(msg.id);
  if (msg.error) p.reject(new RpcError(msg.error.code, msg.error.message));
  else p.resolve(msg.result);
});

export interface Call<T> {
  id: number;
  result: Promise<T>;
  cancel(): void;
}

export function start<T = unknown>(method: string, params: object = {}, hooks: CallHooks = {}): Call<T> {
  const id = nextId++;
  const result = new Promise<T>((resolve, reject) => {
    pending.set(id, { resolve, reject, ...hooks });
  });
  window.backend.send({ jsonrpc: "2.0", id, method, params });
  return { id, result, cancel: () => void call("cancel", { id }) };
}

export function call<T = unknown>(method: string, params: object = {}, hooks: CallHooks = {}): Promise<T> {
  return start<T>(method, params, hooks).result;
}

export function handle(method: string, fn: ServerRequestHandler) {
  handlers.set(method, fn);
}

export function onReady(fn: () => void) {
  readyListeners.add(fn);
  return () => readyListeners.delete(fn);
}

/** Das Backend ist weg: alles Offene scheitert, statt ewig zu warten. */
export function failAll(message: string) {
  for (const [id, p] of pending) {
    p.reject(new RpcError(-32603, message));
    pending.delete(id);
  }
}
