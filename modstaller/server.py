"""Backend for the graphical interface: JSON-RPC 2.0 over stdio.

One message per line. The interface (gui/) starts ``modstaller serve`` as a
child process and is just another client of the existing logic - like
``cli.py``.

Three things go beyond what a request-response loop can do:

* **Running work reports back.** Install, renew and JIT send ``log`` and
  ``progress`` as notifications, tagged with the ID of the request they
  belong to.
* **Running work can be cancelled.** ``cancel`` with that ID. Essential for
  JIT: it waits until the app detaches.
* **Login asks back.** The 2FA code comes from the interface; for that the
  server in turn sends a ``prompt.2fa`` request.

stdout belongs to the protocol alone. Anything else that wants to go there -
a forgotten ``print``, a chatty library - ends up on stderr.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import sys
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Awaitable, Callable

from . import config, logbook
from .errors import describe
from .i18n import _, _n, available, language, set_language
from .logbook import SUCCESS

#: JSON-RPC error codes. Our own ones live in the reserved range below.
PARSE_ERROR = -32700
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
USER_ERROR = -32000        # ModStallerError & co. - message is for humans
CANCELLED = -32800


#: How long a device entry in the status stays valid before the battery is
#: read again. Shorter is not worth it: rebuilding lockdown every time costs.
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
    """A running request: can report back and be cancelled."""

    def __init__(self, server: "Server", req_id) -> None:
        self.server = server
        self.id = req_id
        self._cancel: Callable[[], None] | None = None
        self.cancelled = False
        #: Area in the log - set for actions, None for polling.
        self.source: str | None = None

    def log(self, text: str) -> None:
        self.server.notify("log", {"job": self.id, "text": text})
        if self.source:
            logbook.log(self.source, text, job=self.id)

    def progress(self, pct: int) -> None:
        self.server.notify("progress", {"job": self.id, "pct": pct})

    def cancel(self) -> None:
        self.cancelled = True
        if self._cancel is not None:
            self._cancel()

    async def isolated(self, make_coro: Callable[[], Awaitable[object]]):
        """Runs work in its own thread with its own event loop.

        The pipeline calls Apple synchronously and would otherwise block the
        server loop for seconds - then neither the status nor a ``cancel``
        would get through.
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
        #: Serial -> status fields. The status is polled every few seconds;
        #: rebuilding lockdown for it every time would be expensive.
        self.device_cache: dict[str, dict] = {}
        #: Serial -> what the log last said about it (see _log_device_changes).
        self.seen_devices: dict[str, dict] = {}
        #: New log entries go to the interface as they happen.
        self.book = logbook.BOOK
        self._unsubscribe = self.book.subscribe(
            lambda entry: self.notify("log.entry", entry.as_dict()))

    # -- Sending -----------------------------------------------------------

    def send(self, msg: dict) -> None:
        data = (json.dumps(msg, ensure_ascii=False, default=_jsonable)
                + "\n").encode()
        # Called from several threads - a line must never be torn apart.
        with self._lock:
            view = memoryview(data)
            while view:
                n = os.write(self._out, view)
                view = view[n:]

    def notify(self, name: str, params: dict) -> None:
        self.send({"jsonrpc": "2.0", "method": name, "params": params})

    async def ask(self, name: str, params: dict | None = None):
        """Asks the interface a question and waits for the answer."""
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
        """:meth:`ask` from within a worker thread."""
        return asyncio.run_coroutine_threadsafe(
            self.ask(name, params), self.loop).result()

    # -- Receiving ---------------------------------------------------------

    def handle_line(self, line: bytes) -> None:
        line = line.strip()
        if not line:
            return
        try:
            msg = json.loads(line)
            if not isinstance(msg, dict):
                raise ValueError("not a JSON object message")
        except ValueError as exc:
            self.send({"jsonrpc": "2.0", "id": None, "error": {
                "code": PARSE_ERROR,
                "message": _("Invalid JSON: {error}", error=exc)}})
            return

        if "method" not in msg:
            # Answer to one of our questions.
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
        action = _ACTIONS.get(name) if isinstance(params, dict) else None
        if action is not None:
            job.source = action.source
            _log_safely(action.source, action.start, params, job=req_id)
        try:
            fn = METHODS.get(name)
            if fn is None:
                raise RpcError(METHOD_NOT_FOUND,
                               _("Unknown method: {name}", name=name))
            if not isinstance(params, dict):
                raise RpcError(INVALID_PARAMS, _("params must be an object"))
            result = await fn(self, job, params)
            reply = {"result": result}
            if action is not None:
                _log_safely(action.source, action.done, params, result,
                            job=req_id)
        except RpcError as exc:
            reply = {"error": {"code": exc.code, "message": str(exc)}}
            if action is not None:
                action.log_failure(str(exc), req_id)
        except (_Cancelled, asyncio.CancelledError):
            reply = {"error": {"code": CANCELLED,
                               "message": _("Cancelled.")}}
            if action is not None:
                logbook.log(action.source, _("Cancelled."), logging.WARNING,
                            job=req_id)
        except Exception as exc:
            text = describe(exc)
            if text is None:
                traceback.print_exc(file=sys.stderr)
                text = _("Unexpected error: {kind}: {error}",
                         kind=type(exc).__name__, error=exc)
                code = INTERNAL_ERROR
            else:
                code = USER_ERROR
            reply = {"error": {"code": code, "message": text}}
            if action is not None:
                action.log_failure(text, req_id)
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

    async def serve(self, stream) -> None:
        """Processes lines from ``stream`` (binary, blocking) until EOF.

        Reading happens in a separate thread instead of with
        ``loop.connect_read_pipe``: on Windows that cannot cope with the
        anonymous pipes Electron creates. A thread works everywhere.
        """
        self.loop = asyncio.get_running_loop()
        lines: asyncio.Queue = asyncio.Queue()

        def read() -> None:
            for line in iter(stream.readline, b""):
                self.loop.call_soon_threadsafe(lines.put_nowait, line)
            self.loop.call_soon_threadsafe(lines.put_nowait, None)

        threading.Thread(target=read, name="stdin", daemon=True).start()
        while (line := await lines.get()) is not None:
            self.handle_line(line)
        # Interface gone: cancel running work rather than orphaning it.
        for job in list(self._jobs.values()):
            job.cancel()
        for task in list(self._tasks):
            task.cancel()


# -- The log -------------------------------------------------------------------


class _Action:
    """How a method that changes something appears in the log.

    ``start`` and ``done`` build the message from the parameters (and the
    result); ``done`` returns ``(level, text)``. Polling - status, version,
    lists - stays out of the log, or it would drown everything else.
    Parameters go in only through these functions, so a password never
    does.
    """

    def __init__(self, source: str, start, done, failed: Callable[[str], str]):
        self.source = source
        self.start = start
        self.done = done
        self.failed = failed

    def log_failure(self, error: str, job) -> None:
        logbook.log(self.source, self.failed(error), logging.ERROR, job=job)


def _log_safely(source: str, build, *args, job=None) -> None:
    """Logs what ``build`` returns - a message that cannot be built (a
    result of an unexpected shape) must not fail the request."""
    if build is None:
        return
    try:
        out = build(*args)
    except Exception:
        return
    level, text = out if isinstance(out, tuple) else (logging.INFO, out)
    logbook.log(source, text, level, job=job)


def _file_name(params: dict) -> str:
    return Path(str(params.get("path") or "")).name


def _jit_done(params: dict, r: dict):
    ok = r.get("preparedRegions") or r.get("txm") is False
    return (SUCCESS if ok else logging.WARNING), r["summary"]


def _refresh_done(params: dict, r: list):
    if not r:
        return logging.INFO, _("Nothing was due.")
    return SUCCESS, _n("Renewed {count} app.", "Renewed {count} apps.",
                       len(r))


_ACTIONS: dict[str, _Action] = {
    "install": _Action(
        logbook.INSTALL,
        lambda p: _("Installing {file}", file=_file_name(p)),
        lambda p, r: (SUCCESS, _(
            "{name} installed as {bundle_id} - valid for {days} days",
            name=r["name"], bundle_id=r["bundleId"],
            days=round(r["daysValid"]))),
        lambda e: _("Installation failed: {error}", error=e)),
    "refresh": _Action(
        logbook.REFRESH,
        lambda p: (_("Renewing {bundle_id}", bundle_id=p["bundleId"])
                   if p.get("bundleId") else _("Renewing apps that are due")),
        _refresh_done,
        lambda e: _("Renewal failed: {error}", error=e)),
    "uninstall": _Action(
        logbook.APPS,
        lambda p: _("Removing {bundle_id}", bundle_id=p.get("bundleId", "")),
        lambda p, r: (SUCCESS, _("{bundle_id} removed",
                                 bundle_id=p.get("bundleId", ""))),
        lambda e: _("Removal failed: {error}", error=e)),
    "jit": _Action(
        logbook.JIT,
        lambda p: _("Enabling JIT for {bundle_id}",
                    bundle_id=p.get("bundleId", "")),
        _jit_done,
        lambda e: _("JIT failed: {error}", error=e)),
    "login": _Action(
        logbook.ACCOUNT,
        lambda p: _("Signing in as {apple_id}",
                    apple_id=logbook.mask_apple_id(str(p.get("appleId", "")))),
        lambda p, r: (SUCCESS, _(
            "Signed in as {apple_id}",
            apple_id=logbook.mask_apple_id(str(p.get("appleId", ""))))),
        lambda e: _("Sign-in failed: {error}", error=e)),
    "logout": _Action(
        logbook.ACCOUNT, None,
        lambda p, r: (SUCCESS, _("Signed out.")),
        lambda e: _("Sign-out failed: {error}", error=e)),
    "certs.revoke": _Action(
        logbook.ACCOUNT, None,
        lambda p, r: (SUCCESS, _("Certificate revoked.")),
        lambda e: _("Revoking the certificate failed: {error}", error=e)),
    "appids.delete": _Action(
        logbook.ACCOUNT, None,
        lambda p, r: (SUCCESS, _("App ID deleted.")),
        lambda e: _("Deleting the App ID failed: {error}", error=e)),
    "device.fix": _Action(
        logbook.DEVICE, None,
        lambda p, r: (SUCCESS, r["message"]),
        lambda e: _("Fix failed: {error}", error=e)),
}


def _log_device_changes(server, serials: list[str], device: dict | None,
                        error: str) -> None:
    """Plugging in, unplugging and Developer Mode - once per change.

    Called on every status poll, so it only speaks when something is
    different from what it said last time.
    """
    seen = server.seen_devices
    for gone in set(seen) - set(serials):
        name = seen.pop(gone).get("name") or "iPhone"
        logbook.log(logbook.DEVICE, _("{name} disconnected", name=name))
    if not serials:
        return

    serial = serials[0]
    before = seen.get(serial)
    if device is None:
        if error and (before is None or before.get("error") != error):
            logbook.log(logbook.DEVICE,
                        _("iPhone plugged in but not ready: {error}",
                          error=error), logging.WARNING)
            seen[serial] = {**(before or {}), "error": error}
        return

    now = {"name": device.get("name") or "iPhone",
           "devMode": device.get("developerMode"), "error": ""}
    if before is None or not before.get("name"):
        logbook.log(logbook.DEVICE, _(
            "iPhone connected: {name} · {model} · iOS {version}",
            name=now["name"], model=device.get("model", ""),
            version=device.get("iosVersion", "")))
        if now["devMode"] is False:
            logbook.log(logbook.DEVICE, _(
                "Developer Mode is off - sideloaded apps will not start."),
                logging.WARNING)
    elif before.get("devMode") != now["devMode"]:
        if now["devMode"]:
            logbook.log(logbook.DEVICE, _("Developer Mode is now on."),
                        SUCCESS)
        else:
            logbook.log(logbook.DEVICE, _(
                "Developer Mode is off - sideloaded apps will not start."),
                logging.WARNING)
    seen[serial] = now


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


# -- Methods -----------------------------------------------------------------


def _need(params: dict, key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise RpcError(INVALID_PARAMS,
                       _("Parameter {key!r} is missing", key=key))
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
        # The battery changes - after BATTERY_TTL the entry counts as stale.
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

    _log_device_changes(server, serials, device, st.error or "")
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
            "detachedCleanly": r.detached_cleanly, "txm": r.txm}


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
        raise AppleError(_("Not signed in."))
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
        job.log("Preparing Anisette …")
        ani = _anisette()
        job.log("Signing in to Apple …")
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
    from .device.connection import ServiceProvider
    from .device.install import app_origin, list_apps
    from .provisioning import Capabilities, app_id_in_use
    from .state import store

    # An App ID is not only taken by what ModStaller installed: an app from
    # another tool can just as well depend on it. Without the device, "free"
    # would appear next to an App ID whose deletion breaks a working app.
    # But the iPhone is not always there - then we would rather say so than
    # guess (``usageKnown``).
    protected = {r.bundle_id for r in store.all_installs()}
    usage_known = False
    try:
        async def read():
            async with ServiceProvider() as sp:
                return await list_apps(sp)

        apps = await job.isolated(read)
        protected |= {b for b, m in apps.items() if app_origin(m)["sideloaded"]}
        usage_known = True
    except Exception:
        pass    # No iPhone plugged in - the account page stays usable.

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
                "appIds": [{"appIdId": a.app_id_id, "identifier": a.identifier,
                            "name": a.name,
                            "inUse": app_id_in_use(a.identifier, protected)}
                           for a in app_ids],
                "usageKnown": usage_known,
                "maxAppIdsPerWeek": caps.max_app_ids_per_week,
                "maxAppsPerDevice": caps.max_apps_per_device,
            })
        return out

    return await asyncio.to_thread(run)


@method("appids.delete")
async def _appids_delete(server: Server, job: Job, params: dict):
    """Deletes an App ID in the Apple account.

    Gives *no* weekly quota back: Apple counts newly created App IDs in a
    rolling seven-day window, not the existing ones. Anyone who wants to
    tidy up can do so here; it does not help anyone who wants to install
    again - for that ModStaller falls back to a free App ID on its own (see
    provisioning.ensure_app_id).
    """
    from .provisioning import pick_team
    app_id_id = _need(params, "appIdId")

    def run():
        api = _api()
        team = pick_team(api.list_teams(), params.get("teamId"))
        api.delete_app_id(team.team_id, app_id_id)

    await asyncio.to_thread(run)
    return True


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
    from .device.install import app_origin, list_apps

    async def run():
        async with ServiceProvider() as sp:
            return await list_apps(sp)

    apps = await job.isolated(run)
    return sorted(
        ({"bundleId": bid, "name": _app_name(bid, meta),
          "version": meta.get("CFBundleShortVersionString", ""),
          **app_origin(meta)}
         for bid, meta in apps.items()),
        key=lambda a: a["name"].lower())


def _app_name(bundle_id: str, meta: dict) -> str:
    return (meta.get("CFBundleDisplayName") or meta.get("CFBundleName")
            or bundle_id)


def _record_fields(rec) -> dict:
    """What ModStaller knows about an app it installed itself."""
    from .status import URGENT_DAYS
    if rec is None:
        return {"sourceIpa": "", "sourceMissing": False,
                "originalBundleId": "", "appIdId": "", "expiresAt": None,
                "daysLeft": None, "expiryText": "", "urgent": False,
                "installedAt": None}
    return {
        "sourceIpa": rec.source_ipa,
        "sourceMissing": not Path(rec.source_ipa).is_file(),
        "originalBundleId": rec.original_bundle_id,
        "appIdId": rec.app_id_id,
        "expiresAt": rec.expires_at,
        "daysLeft": rec.days_left,
        "expiryText": rec.expiry_text,
        "urgent": rec.days_left <= URGENT_DAYS,
        "installedAt": rec.installed_at,
    }


@method("apps.overview")
async def _apps_overview(server: Server, job: Job, params: dict):
    """Everything sideloaded on the iPhone - ours and foreign, with origin.

    In one place: what ModStaller installed (including source IPA and
    expiry) and what another tool put there. Foreign apps can only be
    removed, not renewed - the original IPA and the private key live with
    the other tool.

    Entries ModStaller knows about but which are no longer on the device
    are included with ``onDevice: false``: otherwise it would be
    unexplainable why they still take up App IDs.
    """
    from .device.connection import ServiceProvider
    from .device.install import app_origin, list_apps
    from .state import store

    async def run():
        async with ServiceProvider() as sp:
            return await list_apps(sp)

    apps = await job.isolated(run)
    records = {r.bundle_id: r for r in store.all_installs()}

    out = []
    for bid, meta in apps.items():
        origin = app_origin(meta)
        rec = records.pop(bid, None)
        if not origin["sideloaded"] and rec is None:
            continue
        out.append({"bundleId": bid, "name": _app_name(bid, meta),
                    "version": meta.get("CFBundleShortVersionString", ""),
                    "onDevice": True, "managed": rec is not None,
                    **origin, **_record_fields(rec)})

    for bid, rec in records.items():
        out.append({"bundleId": bid, "name": rec.name, "version": "",
                    "onDevice": False, "managed": True, "signer": "",
                    "teamId": rec.team_id, "sideloaded": True,
                    "developerSigned": True, **_record_fields(rec)})

    out.sort(key=lambda a: (not a["managed"], a["name"].lower()))
    return out


@method("device.checks")
async def _device_checks(server: Server, job: Job, params: dict):
    from .device.readiness import run_checks
    return [asdict(c) for c in await job.isolated(run_checks)]


@method("device.fix")
async def _device_fix(server: Server, job: Job, params: dict):
    from .device.readiness import run_fix
    fix = _need(params, "fix")
    result = await job.isolated(lambda: run_fix(fix, on_step=job.log))
    # Developer Mode & co. live in the status cache - it is now outdated.
    server.device_cache.clear()
    return asdict(result)


@method("log.history")
async def _log_history(server: Server, job: Job, params: dict):
    """What happened before the interface connected (newest last)."""
    limit = params.get("limit")
    return [e.as_dict() for e in server.book.history(
        limit if isinstance(limit, int) and limit > 0 else None)]


@method("log.path")
async def _log_path(server: Server, job: Job, params: dict):
    return str(config.LOG_FILE)


@method("cancel")
async def _cancel(server: Server, job: Job, params: dict):
    return server.cancel(params.get("id"))


@method("info")
async def _info(server: Server, job: Job, params: dict):
    return {"version": await _version(server, job, params),
            "dataDir": str(config.DATA_DIR), "posix": config.POSIX,
            "language": language(), "languages": available()}


@method("i18n.set")
async def _i18n_set(server: Server, job: Job, params: dict):
    """Tells the backend which language to answer in.

    The interface sends this right after connecting and on every change.
    Returns the language actually in effect - one we do not have falls back
    to English.
    """
    return set_language(_need(params, "language"))


@method("version")
async def _version(server: Server, job: Job, params: dict):
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("modstaller")
    except PackageNotFoundError:
        return "dev"


# -- Entry point -------------------------------------------------------------


def take_stdout() -> int:
    """Keeps stdout for the protocol and redirects everything else.

    At the FD level, so that C extensions and child processes writing to
    FD 1 do not pollute the protocol either.
    """
    sys.stdout.flush()
    out = os.dup(1)
    os.dup2(2, 1)
    if os.name == "nt":
        # On Windows child processes inherit not FD 1 but the process's
        # standard handle - dup2 does not redirect that.
        import ctypes
        import msvcrt
        STD_OUTPUT_HANDLE = -11
        ctypes.windll.kernel32.SetStdHandle(STD_OUTPUT_HANDLE,
                                            msvcrt.get_osfhandle(2))
    sys.stdout = sys.stderr
    return out


async def _run() -> int:
    out = take_stdout()
    logbook.setup(file=config.LOG_FILE)
    server = Server(out)
    server.notify("ready", {})
    await server.serve(sys.stdin.buffer)
    return 0


def main() -> int:
    config.ensure_dirs()
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        return 130
