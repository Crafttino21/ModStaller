"""Backend fuer die grafische Oberflaeche: JSON-RPC 2.0 ueber stdio.

Eine Nachricht pro Zeile. Die Oberflaeche (gui/) startet ``modstaller serve``
als Kindprozess und ist nur ein weiterer Client der vorhandenen Logik - wie
``cli.py`` auch.

Drei Dinge gehen ueber das, was eine Anfrage-Antwort-Schleife kann:

* **Laufende Arbeit meldet sich.** Installieren, Erneuern und JIT schicken
  ``log`` und ``progress`` als Notification, gekennzeichnet mit der ID der
  Anfrage, zu der sie gehoeren.
* **Laufende Arbeit laesst sich abbrechen.** ``cancel`` mit dieser ID. Fuer
  JIT unverzichtbar: es wartet, bis sich die App abmeldet.
* **Der Login fragt zurueck.** Der 2FA-Code kommt aus der Oberflaeche; der
  Server stellt dafuer seinerseits eine Anfrage ``prompt.2fa``.

stdout gehoert allein dem Protokoll. Alles, was sonst dorthin will - ein
vergessenes ``print``, eine gespraechige Bibliothek -, landet auf stderr.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import os
import sys
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Awaitable, Callable

from . import config
from .errors import describe

#: JSON-RPC-Fehlercodes. Eigene liegen im freigegebenen Bereich darunter.
PARSE_ERROR = -32700
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
USER_ERROR = -32000        # ModStallerError & Co. - Meldung ist fuer Menschen
CANCELLED = -32800


#: Wie lange ein Geraete-Eintrag im Status gilt, bevor der Akku neu gelesen
#: wird. Kuerzer lohnt nicht: lockdown jedes Mal neu aufzubauen kostet.
BATTERY_TTL = 30.0


class RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


class _Cancelled(Exception):
    pass


Handler = Callable[["Server", "Job", dict], Awaitable[object]]
METHODS: dict[str, Handler] = {}


def method(name: str):
    def register(fn: Handler) -> Handler:
        METHODS[name] = fn
        return fn
    return register


class Job:
    """Eine laufende Anfrage: kann melden und abgebrochen werden."""

    def __init__(self, server: "Server", req_id) -> None:
        self.server = server
        self.id = req_id
        self._cancel: Callable[[], None] | None = None
        self.cancelled = False

    def log(self, text: str) -> None:
        self.server.notify("log", {"job": self.id, "text": text})

    def progress(self, pct: int) -> None:
        self.server.notify("progress", {"job": self.id, "pct": pct})

    def cancel(self) -> None:
        self.cancelled = True
        if self._cancel is not None:
            self._cancel()

    async def isolated(self, make_coro: Callable[[], Awaitable[object]]):
        """Fuehrt eine Arbeit in eigenem Thread mit eigenem Event-Loop aus.

        Die Pipeline ruft Apple synchron auf und wuerde den Server-Loop sonst
        sekundenlang blockieren - dann kaeme weder der Status noch ein
        ``cancel`` durch.
        """
        def runner():
            loop = asyncio.new_event_loop()
            task = loop.create_task(make_coro())
            self._cancel = lambda: loop.call_soon_threadsafe(task.cancel)
            if self.cancelled:
                task.cancel()
            try:
                return loop.run_until_complete(task)
            except asyncio.CancelledError:
                raise _Cancelled() from None
            finally:
                loop.close()

        try:
            return await asyncio.to_thread(runner)
        finally:
            self._cancel = None


class Server:
    def __init__(self, out_fd: int) -> None:
        self._out = out_fd
        self._lock = threading.Lock()
        self._jobs: dict[object, Job] = {}
        self._pending: dict[str, asyncio.Future] = {}
        self._ids = itertools.count(1)
        self._tasks: set[asyncio.Task] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        #: Serial -> Status-Felder. Der Status wird alle paar Sekunden
        #: abgefragt; lockdown dafuer jedes Mal neu aufzubauen waere teuer.
        self.device_cache: dict[str, dict] = {}

    # -- Senden ------------------------------------------------------------

    def send(self, msg: dict) -> None:
        data = (json.dumps(msg, ensure_ascii=False, default=_jsonable)
                + "\n").encode()
        # Aus mehreren Threads aufgerufen - eine Zeile darf nie zerreissen.
        with self._lock:
            view = memoryview(data)
            while view:
                n = os.write(self._out, view)
                view = view[n:]

    def notify(self, name: str, params: dict) -> None:
        self.send({"jsonrpc": "2.0", "method": name, "params": params})

    async def ask(self, name: str, params: dict | None = None):
        """Stellt der Oberflaeche eine Frage und wartet auf die Antwort."""
        req_id = f"s{next(self._ids)}"
        fut = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        try:
            self.send({"jsonrpc": "2.0", "id": req_id, "method": name,
                       "params": params or {}})
            return await fut
        finally:
            self._pending.pop(req_id, None)

    def ask_blocking(self, name: str, params: dict | None = None):
        """:meth:`ask` aus einem Worker-Thread heraus."""
        return asyncio.run_coroutine_threadsafe(
            self.ask(name, params), self.loop).result()

    # -- Empfangen ---------------------------------------------------------

    def handle_line(self, line: bytes) -> None:
        line = line.strip()
        if not line:
            return
        try:
            msg = json.loads(line)
            if not isinstance(msg, dict):
                raise ValueError("keine JSON-Objekt-Nachricht")
        except ValueError as exc:
            self.send({"jsonrpc": "2.0", "id": None, "error": {
                "code": PARSE_ERROR, "message": f"Ungueltiges JSON: {exc}"}})
            return

        if "method" not in msg:
            # Antwort auf eine unserer Fragen.
            fut = self._pending.get(msg.get("id"))
            if fut is not None and not fut.done():
                if "error" in msg:
                    fut.set_exception(RpcError(
                        msg["error"].get("code", INTERNAL_ERROR),
                        msg["error"].get("message", "")))
                else:
                    fut.set_result(msg.get("result"))
            return

        task = asyncio.get_running_loop().create_task(self._dispatch(msg))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _dispatch(self, msg: dict) -> None:
        req_id = msg.get("id")
        name = msg["method"]
        params = msg.get("params") or {}
        job = Job(self, req_id)
        if req_id is not None:
            self._jobs[req_id] = job
        try:
            fn = METHODS.get(name)
            if fn is None:
                raise RpcError(METHOD_NOT_FOUND, f"Unbekannte Methode: {name}")
            if not isinstance(params, dict):
                raise RpcError(INVALID_PARAMS, "params muss ein Objekt sein")
            result = await fn(self, job, params)
            reply = {"result": result}
        except RpcError as exc:
            reply = {"error": {"code": exc.code, "message": str(exc)}}
        except (_Cancelled, asyncio.CancelledError):
            reply = {"error": {"code": CANCELLED, "message": "Abgebrochen."}}
        except Exception as exc:
            text = describe(exc)
            if text is None:
                traceback.print_exc(file=sys.stderr)
                text = f"Unerwarteter Fehler: {type(exc).__name__}: {exc}"
                code = INTERNAL_ERROR
            else:
                code = USER_ERROR
            reply = {"error": {"code": code, "message": text}}
        finally:
            self._jobs.pop(req_id, None)
        if req_id is not None:
            self.send({"jsonrpc": "2.0", "id": req_id, **reply})

    def cancel(self, req_id) -> bool:
        job = self._jobs.get(req_id)
        if job is None:
            return False
        job.cancel()
        return True

    async def serve(self, reader: asyncio.StreamReader) -> None:
        self.loop = asyncio.get_running_loop()
        while True:
            line = await reader.readline()
            if not line:
                break
            self.handle_line(line)
        # Oberflaeche weg: laufende Arbeit abbrechen, nicht verwaisen lassen.
        for job in list(self._jobs.values()):
            job.cancel()
        for task in list(self._tasks):
            task.cancel()


def _jsonable(obj):
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return None
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return str(obj)


# -- Methoden ----------------------------------------------------------------


def _need(params: dict, key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise RpcError(INVALID_PARAMS, f"Parameter {key!r} fehlt")
    return value


def _app_dict(rec) -> dict:
    from .status import URGENT_DAYS
    return {
        "bundleId": rec.bundle_id,
        "originalBundleId": rec.original_bundle_id,
        "name": rec.name,
        "daysLeft": rec.days_left,
        "expiresAt": rec.expires_at,
        "expiryText": rec.expiry_text,
        "urgent": rec.days_left <= URGENT_DAYS,
        "sourceIpa": rec.source_ipa,
        "sourceMissing": not Path(rec.source_ipa).is_file(),
    }


def _outcome_dict(o) -> dict:
    return {"bundleId": o.bundle_id, "name": o.name, "transport": o.transport,
            "daysValid": o.days_valid,
            "strippedExtensions": o.stripped_extensions}


@method("status")
async def _status(server: Server, job: Job, params: dict):
    from .apple.session import Session
    from .device.connection import list_devices
    from .device.models import form_factor, marketing_name
    from .state import store
    from .status import URGENT_DAYS, Status, device_status

    st = Status(apps=store.all_installs(), logged_in=Session.load() is not None)
    serials = await list_devices()
    cache = server.device_cache
    for gone in set(cache) - set(serials):
        del cache[gone]

    device = None
    if serials:
        entry = cache.get(serials[0])
        # Der Akku aendert sich - nach BATTERY_TTL gilt der Eintrag als alt.
        stale = entry is None or time.monotonic() - entry["_at"] > BATTERY_TTL
        if stale or params.get("refresh"):
            cache.pop(serials[0], None)
            await device_status(st)
            if st.has_device and not st.error:
                cache[serials[0]] = {
                    "_at": time.monotonic(),
                    "name": st.device_name, "udid": st.udid,
                    "iosVersion": st.ios_version,
                    "developerMode": st.developer_mode,
                    "productType": st.product_type,
                    "model": marketing_name(st.product_type),
                    "formFactor": form_factor(st.product_type),
                    "battery": ({"level": st.battery.level,
                                 "charging": st.battery.charging}
                                if st.battery else None),
                }
        if serials[0] in cache:
            device = {k: v for k, v in cache[serials[0]].items()
                      if not k.startswith("_")}

    return {
        "device": device,
        "deviceAttached": bool(serials),
        "loggedIn": st.logged_in,
        "apps": [_app_dict(a) for a in st.apps],
        "urgent": [a.bundle_id for a in st.urgent],
        "urgentDays": URGENT_DAYS,
        "error": st.error,
    }


@method("doctor")
async def _doctor(server: Server, job: Job, params: dict):
    from .doctor import run_checks
    return [asdict(c) for c in await run_checks()]


@method("ipa.find")
async def _ipa_find(server: Server, job: Job, params: dict):
    from .status import find_ipas
    return [{"path": str(p), "name": p.name, "size": p.stat().st_size,
             "modified": p.stat().st_mtime} for p in find_ipas()]


@method("ipa.inspect")
async def _ipa_inspect(server: Server, job: Job, params: dict):
    from .signing.ipa import inspect
    info = await asyncio.to_thread(inspect, Path(_need(params, "path")))
    return {"path": str(info.path), "bundleId": info.bundle_id,
            "name": info.name, "version": info.version,
            "minimumOs": info.minimum_os, "extensions": info.extensions,
            "frameworks": info.frameworks, "dylibs": info.dylibs,
            "encrypted": info.encrypted,
            "size": info.path.stat().st_size}


@method("install")
async def _install(server: Server, job: Job, params: dict):
    from .pipeline import install

    path = Path(_need(params, "path")).expanduser()
    keep = params.get("keepExtensions")
    outcome = await job.isolated(lambda: install(
        path, strip_extensions=False if keep else None,
        revoke_conflicting_cert=bool(params.get("revokeConflictingCert")),
        progress=job.progress, on_step=job.log))
    return _outcome_dict(outcome)


@method("refresh")
async def _refresh(server: Server, job: Job, params: dict):
    from .pipeline import refresh
    results = await job.isolated(lambda: refresh(
        only=params.get("bundleId"), threshold_days=params.get("threshold"),
        progress=job.progress, on_step=job.log))
    return [_outcome_dict(o) for o in results]


@method("uninstall")
async def _uninstall(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider
    from .device.install import uninstall_app
    from .state import store

    bundle_id = _need(params, "bundleId")

    async def run():
        async with ServiceProvider() as sp:
            return await uninstall_app(sp, bundle_id)

    transport = await job.isolated(run)
    return {"transport": transport, "forgotten": store.forget(bundle_id)}


@method("jit")
async def _jit(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider
    from .device.jit import enable_jit

    bundle_id = _need(params, "bundleId")

    async def run():
        async with ServiceProvider() as sp:
            return await enable_jit(sp, bundle_id, on_step=job.log)

    r = await job.isolated(run)
    return {"summary": r.summary, "notes": r.notes, "pid": r.pid,
            "preparedRegions": r.prepared_regions,
            "preparedBytes": r.prepared_bytes,
            "detachedCleanly": r.detached_cleanly}


def _anisette():
    from .apple import anisette as anisette_mod
    s = config.Settings.load()
    return anisette_mod.build(s.anisette_provider, s.anisette_server)


def _api():
    from .apple.devservices import DeveloperServices
    from .apple.session import Session
    from .errors import AppleError
    session = Session.load()
    if session is None:
        raise AppleError("Nicht angemeldet.")
    return DeveloperServices(session, _anisette())


@method("login")
async def _login(server: Server, job: Job, params: dict):
    from .apple.devservices import DeveloperServices
    from .apple.session import login

    apple_id = _need(params, "appleId").strip()
    password = _need(params, "password")

    def prompt_code() -> str:
        return server.ask_blocking("prompt.2fa") or ""

    def run():
        job.log("Anisette vorbereiten …")
        ani = _anisette()
        job.log("Bei Apple anmelden …")
        session = login(apple_id, password, ani, code_prompt=prompt_code)
        return [str(t) for t in DeveloperServices(session, ani).list_teams()]

    return {"teams": await asyncio.to_thread(run)}


@method("logout")
async def _logout(server: Server, job: Job, params: dict):
    from .apple.session import Session
    Session.clear()
    if params.get("forgetDevice"):
        from .apple.anisette import DEVICE_FILE, PROVISIONING_FILE
        for f in (PROVISIONING_FILE, DEVICE_FILE):
            f.unlink(missing_ok=True)
    return True


@method("account")
async def _account(server: Server, job: Job, params: dict):
    from .provisioning import Capabilities

    def run():
        api = _api()
        out = []
        for team in api.list_teams():
            caps = Capabilities.for_team(team)
            app_ids = api.list_app_ids(team.team_id)
            out.append({
                "teamId": team.team_id, "name": team.name, "type": team.type,
                "isFree": caps.is_free, "description": caps.describe(),
                "devices": len(api.list_devices(team.team_id)),
                "appIds": [a.identifier for a in app_ids],
                "maxAppIdsPerWeek": caps.max_app_ids_per_week,
                "maxAppsPerDevice": caps.max_apps_per_device,
            })
        return out

    return await asyncio.to_thread(run)


def _cert_dict(c) -> dict:
    return {"certId": c.cert_id, "serial": c.serial, "name": c.name,
            "machineId": c.machine_id,
            "expiresAt": c.expires_at.isoformat() if c.expires_at else None}


@method("certs.list")
async def _certs_list(server: Server, job: Job, params: dict):
    from .provisioning import pick_team

    def run():
        api = _api()
        team = pick_team(api.list_teams(), params.get("teamId"))
        return {"teamId": team.team_id,
                "certs": [_cert_dict(c)
                          for c in api.list_certificates(team.team_id)]}

    return await asyncio.to_thread(run)


@method("certs.revoke")
async def _certs_revoke(server: Server, job: Job, params: dict):
    from .provisioning import pick_team
    serial = _need(params, "serial")

    def run():
        api = _api()
        team = pick_team(api.list_teams(), params.get("teamId"))
        api.revoke_certificate(team.team_id, serial)

    await asyncio.to_thread(run)
    return True


@method("device.info")
async def _device_info(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider, device_info
    async with ServiceProvider() as sp:
        info = await device_info(sp.lockdown)
    return {"udid": info.udid, "name": info.name,
            "productType": info.product_type, "iosVersion": info.ios_version,
            "build": info.build, "developerMode": info.developer_mode}


@method("device.apps")
async def _device_apps(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider
    from .device.install import list_apps

    async def run():
        async with ServiceProvider() as sp:
            return await list_apps(sp)

    apps = await job.isolated(run)
    return sorted(
        ({"bundleId": bid, "name": meta.get("CFBundleDisplayName")
          or meta.get("CFBundleName") or bid,
          "version": meta.get("CFBundleShortVersionString", "")}
         for bid, meta in apps.items()),
        key=lambda a: a["name"].lower())


@method("device.checks")
async def _device_checks(server: Server, job: Job, params: dict):
    from .device.readiness import run_checks
    return [asdict(c) for c in await job.isolated(run_checks)]


@method("device.fix")
async def _device_fix(server: Server, job: Job, params: dict):
    from .device.readiness import run_fix
    fix = _need(params, "fix")
    result = await job.isolated(lambda: run_fix(fix, on_step=job.log))
    # Entwicklermodus & Co. stehen im Status-Cache - der ist jetzt veraltet.
    server.device_cache.clear()
    return asdict(result)


@method("cancel")
async def _cancel(server: Server, job: Job, params: dict):
    return server.cancel(params.get("id"))


@method("version")
async def _version(server: Server, job: Job, params: dict):
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("modstaller")
    except PackageNotFoundError:
        return "dev"


# -- Einstieg ----------------------------------------------------------------


def take_stdout() -> int:
    """Behaelt stdout fuer das Protokoll und leitet alles andere um.

    Auf FD-Ebene, damit auch C-Erweiterungen und Kindprozesse, die auf FD 1
    schreiben, das Protokoll nicht verunreinigen.
    """
    sys.stdout.flush()
    out = os.dup(1)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return out


async def _run() -> int:
    out = take_stdout()
    server = Server(out)
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader(limit=16 * 1024 * 1024)
    await loop.connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    server.notify("ready", {})
    await server.serve(reader)
    return 0


def main() -> int:
    config.ensure_dirs()
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        return 130
