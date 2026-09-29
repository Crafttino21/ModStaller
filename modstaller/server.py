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
        #: Whether the log last said the Apple device service is missing
        #: (Windows). None: nothing said yet.
        self.usb_service_missing: bool | None = None
        #: (monotonic time, winsetup.ServiceState) - asking Windows takes a
        #: PowerShell start, too slow for every status poll.
        self.usb_service_probe: tuple[float, object] | None = None
        #: adsid -> (monotonic time, api, teams, {team_id: (app_ids, quota)}).
        #: The install screen asks for a plan on every edit - Apple is
        #: asked at most every APPLE_CACHE_TTL seconds.
        self.apple_cache: dict[str, tuple[float, object, list, dict]] = {}
        #: Accounts whose first name for the greeting was already looked up.
        self.name_lookups: set[str] = set()
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
            kind = _error_kind(exc)
            if kind is not None:
                reply["error"]["data"] = kind
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


def _error_kind(exc: BaseException) -> dict | None:
    """What kind of error it was - for clients that act on it without a
    person reading the message, like the refresh in the tray."""
    from .errors import ModStallerError
    if isinstance(exc, ModStallerError):
        return {"kind": type(exc).__name__, "exitCode": exc.exit_code}
    if describe(exc) is not None:          # network trouble, see describe()
        return {"kind": "NetworkError", "exitCode": 1}
    return None


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
    "usb.setup": _Action(
        logbook.DEVICE,
        lambda p: _("Setting up the Apple device service"),
        lambda p, r: (SUCCESS, _usb_setup_message(r["method"])),
        lambda e: _("Setting up the Apple device service failed: {error}",
                    error=e)),
    "device.fix": _Action(
        logbook.DEVICE, None,
        lambda p, r: (SUCCESS, r["message"]),
        lambda e: _("Fix failed: {error}", error=e)),
    "device.wifi": _Action(
        logbook.DEVICE,
        lambda p: (_("Switching on Wi-Fi") if p.get("enable")
                   else _("Switching off Wi-Fi")),
        lambda p, r: (SUCCESS, _("Wi-Fi is on.") if p.get("enable")
                      else _("Wi-Fi is off.")),
        lambda e: _("Wi-Fi could not be switched: {error}", error=e)),
    "pair.start": _Action(
        logbook.DEVICE,
        lambda p: _("Pairing {name}", name=p.get("name") or p.get("host", "")),
        lambda p, r: (SUCCESS, _("{name} is paired.", name=r.get("name", ""))),
        lambda e: _("Pairing failed: {error}", error=e)),
    "device.forget": _Action(
        logbook.DEVICE, None,
        lambda p, r: (SUCCESS, _("Device forgotten.")),
        lambda e: _("Forgetting the device failed: {error}", error=e)),
}


#: How long a PowerShell answer about the service stays valid.
USB_PROBE_TTL = 20.0


async def _usb_service_stopped(server) -> bool:
    """Installed but not running? (Otherwise: not installed at all.)"""
    from . import winsetup
    probe = server.usb_service_probe
    if probe is None or time.monotonic() - probe[0] > USB_PROBE_TTL:
        state = await asyncio.to_thread(winsetup.service_state)
        server.usb_service_probe = probe = (time.monotonic(), state)
    return probe[1].state == winsetup.STOPPED


def _log_usb_service(server, missing: bool) -> None:
    """The Apple device service going away or coming back - once per change."""
    before = server.usb_service_missing
    if before == missing:
        return
    server.usb_service_missing = missing
    if missing:
        from .device.connection import usb_service_hint
        logbook.log(logbook.DEVICE, _(
            "Apple device service not reachable - no iPhone can be detected. "
            "{hint}", hint=usb_service_hint()), logging.WARNING)
    elif before:
        logbook.log(logbook.DEVICE, _("Apple device service is reachable again."),
                    SUCCESS)


def _device_kind(device: dict) -> str:
    from .device.models import device_kind
    return device_kind(device.get("productType") or "")


def _os_name(platform: str | None) -> str:
    return {"tvos": "tvOS", "xros": "visionOS"}.get(platform or "", "iOS")


def _log_device_changes(server, refs: list, cache: dict, errors: dict) -> None:
    """Connecting, disconnecting and Developer Mode - once per change.

    Called on every status poll, so it only speaks when something is
    different from what it said last time.
    """
    from .device.discovery import USB, USBMUX_NET
    seen = server.seen_devices
    present = {r.udid for r in refs}
    for gone in set(seen) - present:
        name = seen.pop(gone).get("name") or "iPhone"
        logbook.log(logbook.DEVICE, _("{name} disconnected", name=name))

    for ref in refs:
        udid = ref.udid
        before = seen.get(udid)
        device = cache.get(udid)
        error = errors.get(udid, "")
        if device is None:
            if error and (before is None or before.get("error") != error):
                logbook.log(logbook.DEVICE,
                            _("Device connected but not ready: {error}",
                              error=error), logging.WARNING)
                seen[udid] = {**(before or {}), "error": error}
            continue

        via = _("USB") if ref.transport in (USB,) else _("Wi-Fi")
        if ref.transport == USBMUX_NET:
            via = _("Wi-Fi")
        now = {"name": device.get("name") or _device_kind(device),
               "devMode": device.get("developerMode"), "error": "",
               "transport": ref.transport}
        # Network-only devices report no Developer Mode status we could trust.
        tv = device.get("platform") in ("tvos", "xros")
        if before is None or not before.get("name"):
            logbook.log(logbook.DEVICE, _(
                "Connected: {name} · {model} · {os} {version} · {via}",
                name=now["name"], model=device.get("model", ""),
                os=_os_name(device.get("platform")),
                version=device.get("iosVersion", ""), via=via))
            if now["devMode"] is False:
                logbook.log(logbook.DEVICE, _(
                    "Developer Mode is off - sideloaded apps will not start."),
                    logging.WARNING)
        else:
            # Only the cable/network switch is news - between the two network
            # ways (lockdown, RemotePairing) a device changes all the time.
            was_usb = before.get("transport") == USB
            if before.get("transport") and was_usb != (ref.transport == USB):
                logbook.log(logbook.DEVICE, _("{name} is now connected via {via}.",
                                              name=now["name"], via=via))
            if before.get("devMode") != now["devMode"] and not tv:
                if now["devMode"]:
                    logbook.log(logbook.DEVICE, _("Developer Mode is now on."),
                                SUCCESS)
                else:
                    logbook.log(logbook.DEVICE, _(
                        "Developer Mode is off - sideloaded apps will not start."),
                        logging.WARNING)
        seen[udid] = now


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
    from .pipeline import account_for
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
        "teamId": rec.team_id,
        "adsid": rec.adsid,
        "udid": rec.udid,
        # Can it be renewed without anyone signing in again?
        "accountReady": account_for(rec) is not None,
    }


def _outcome_dict(o) -> dict:
    return {"bundleId": o.bundle_id, "name": o.name, "transport": o.transport,
            "daysValid": o.days_valid,
            "strippedExtensions": o.stripped_extensions,
            "keptExtensions": o.kept_extensions,
            "newAppIds": o.new_app_ids}


def _udid_param(params: dict) -> str | None:
    """The optional ``udid`` a call is about - else the default device."""
    value = params.get("udid")
    return value if isinstance(value, str) and value else None


def _device_entry(st, ref) -> dict:
    """What the status says about one device (cached, see BATTERY_TTL)."""
    from .device.models import form_factor, marketing_name
    return {
        "_at": time.monotonic(),
        "name": st.device_name, "udid": st.udid,
        "iosVersion": st.ios_version,
        "developerMode": st.developer_mode,
        "productType": st.product_type,
        "model": marketing_name(st.product_type),
        "formFactor": form_factor(st.product_type),
        "platform": st.platform,
        "battery": ({"level": st.battery.level,
                     "charging": st.battery.charging}
                    if st.battery else None),
    }


def _device_summary(ref, entry: dict | None) -> dict:
    """One line of the device list - from the cache, else from what
    ModStaller remembers about the device, else just its UDID."""
    from .device import registry
    from .device.models import form_factor, marketing_name
    known = registry.get(ref.udid)
    if entry is not None:
        out = {k: v for k, v in entry.items() if not k.startswith("_")}
    else:
        product = known.product_type if known else ""
        out = {"name": (known.name if known else "") or ref.udid[:8],
               "udid": ref.udid,
               "iosVersion": known.os_version if known else "",
               "developerMode": None,
               "productType": product,
               "model": marketing_name(product) if product else "",
               "formFactor": form_factor(product) if product else "island",
               "platform": known.platform if known else registry.IOS,
               "battery": None}
    out["transport"] = ref.transport
    out["wifiEnabled"] = bool(known and known.wifi_enabled)
    return out


def _pick_selected(refs, wanted: str | None):
    if wanted:
        hit = next((r for r in refs if r.udid == wanted), None)
        if hit is not None:
            return hit
    preferred = config.Settings.load().default_udid
    if preferred:
        hit = next((r for r in refs if r.udid == preferred), None)
        if hit is not None:
            return hit
    return refs[0] if refs else None


@method("status")
async def _status(server: Server, job: Job, params: dict):
    from .apple.session import active_adsid, list_accounts
    from .device import discovery
    from .errors import UsbServiceUnavailable
    from .state import store
    from .status import URGENT_DAYS, Status, device_status

    accounts = list_accounts()
    active = active_adsid()
    session = next((a for a in accounts if a.adsid == active), None)
    for account in accounts:
        if not account.first_name:
            _look_up_first_name(server, account.adsid)
    st = Status(apps=store.all_installs(), logged_in=session is not None)
    try:
        local = await discovery.usbmux_refs()
        usb_service = "ok"
    except UsbServiceUnavailable as exc:
        # Windows without Apple Devices/iTunes: Explorer shows the iPhone,
        # we never will over the cable - say so instead of "not connected".
        local, usb_service = [], "missing"
        st.error = str(exc)
        if await _usb_service_stopped(server):
            usb_service = "stopped"
            st.error = _("The Apple device service is installed but not "
                         "running.")
    _log_usb_service(server, usb_service == "missing")
    # The network search runs in the background - here only what it saw.
    network = discovery.SCANNER.refs() if discovery.SCANNER is not None else []
    refs = discovery.merge(local, network)

    cache = server.device_cache
    for gone in set(cache) - {r.udid for r in refs}:
        del cache[gone]

    errors: dict[str, str] = {}
    for ref in refs:
        entry = cache.get(ref.udid)
        # The battery changes - after BATTERY_TTL the entry counts as stale.
        # A new way to the device (cable pulled, now Wi-Fi) is asked anew.
        stale = (entry is None or time.monotonic() - entry["_at"] > BATTERY_TTL
                 or entry.get("_transport") != ref.transport)
        if not (stale or params.get("refresh")):
            continue
        cache.pop(ref.udid, None)
        one = Status()
        await device_status(one, ref)
        if one.has_device and not one.error:
            cache[ref.udid] = {**_device_entry(one, ref), "_transport": ref.transport}
        elif one.error:
            errors[ref.udid] = one.error

    selected = _pick_selected(refs, _udid_param(params))
    devices = [_device_summary(r, cache.get(r.udid)) for r in refs]
    device = None
    if selected is not None and selected.udid in cache:
        device = _device_summary(selected, cache[selected.udid])
    if selected is not None and not st.error:
        st.error = errors.get(selected.udid, "")

    _log_device_changes(server, refs, cache, errors)
    return {
        "device": device,
        "devices": devices,
        "selectedUdid": selected.udid if selected else None,
        "deviceAttached": bool(refs),
        "attached": [r.udid for r in refs],
        "loggedIn": st.logged_in,
        "firstName": session.first_name if session else "",
        "accounts": [_account_dict(a, active) for a in accounts],
        "apps": [_app_dict(a) for a in st.apps],
        "urgent": [a.bundle_id for a in st.urgent],
        "urgentDays": URGENT_DAYS,
        "error": st.error,
        "usbService": usb_service,
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
    import base64
    from .plan import movable
    from .signing.ipa import icon_png, inspect

    path = Path(_need(params, "path"))
    info = await asyncio.to_thread(inspect, path)
    try:
        png = await asyncio.to_thread(icon_png, path)
    except Exception:
        png = None      # a broken icon must not stop the install
    can_keep = movable(info)
    return {"path": str(info.path), "bundleId": info.bundle_id,
            "name": info.name, "version": info.version,
            "minimumOs": info.minimum_os, "platform": info.platform,
            "deviceFamilies": info.device_families,
            "extensions": info.extensions,
            "extensionDetails": [
                {"path": e.path, "bundleId": e.bundle_id, "name": e.name,
                 "point": e.point, "movable": e.path in can_keep}
                for e in info.extension_details],
            "hasWatch": info.has_watch,
            "icon": ("data:image/png;base64," + base64.b64encode(png).decode()
                     if png else None),
            "frameworks": info.frameworks, "dylibs": info.dylibs,
            "encrypted": info.encrypted,
            "size": info.path.stat().st_size}


def _icon_param(params: dict) -> Path | None:
    """The editor's icon: a PNG as data URL (the interface crops and scales
    it to 1024 px). Written to a temporary file for zsign."""
    import base64
    import uuid
    from .config import WORK_DIR
    from .errors import SigningError

    value = params.get("icon")
    if not value:
        return None
    if not isinstance(value, str) or not value.startswith("data:image/png;base64,"):
        raise SigningError(_("The icon must be a PNG image."))
    data = base64.b64decode(value.split(",", 1)[1], validate=True)
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > 8 * 1024 * 1024:
        raise SigningError(_("The icon must be a PNG image."))
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    target = WORK_DIR / f"icon-{uuid.uuid4().hex[:12]}.png"
    target.write_bytes(data)
    return target


def _keep_param(params: dict) -> list[str] | None:
    keep = params.get("extensions")
    if keep is None:
        return None
    if not isinstance(keep, list) or not all(isinstance(k, str) for k in keep):
        raise RpcError(INVALID_PARAMS, "extensions: list of paths expected")
    return keep


def _text_param(params: dict, key: str) -> str | None:
    value = params.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


@method("install")
async def _install(server: Server, job: Job, params: dict):
    from .pipeline import install

    path = Path(_need(params, "path")).expanduser()
    keep = params.get("keepExtensions")
    icon = _icon_param(params)
    try:
        outcome = await job.isolated(lambda: install(
            path, account=_account_param(params),
            strip_extensions=False if keep else None,
            revoke_conflicting_cert=bool(params.get("revokeConflictingCert")),
            display_name=_text_param(params, "displayName"),
            bundle_id=_text_param(params, "bundleId"),
            icon=icon, keep_extensions=_keep_param(params),
            spare_app_id=_text_param(params, "spareAppId"),
            udid=_udid_param(params),
            progress=job.progress, on_step=job.log))
    finally:
        if icon is not None:
            icon.unlink(missing_ok=True)
        server.apple_cache.clear()      # the App IDs have changed
    return _outcome_dict(outcome)


#: How long a listTeams/listAppIds answer is good for the install screen.
APPLE_CACHE_TTL = 30.0
_APPLE_VIEW_LOCK = threading.Lock()


def _apple_view(server, adsid: str | None, team_id: str | None = None,
                fresh: bool = False):
    """(adsid, team, capabilities, app_ids, quota) - cached briefly."""
    from .apple.session import active_adsid, remember_teams
    from .provisioning import Capabilities, pick_team
    adsid = adsid or active_adsid() or ""
    # One after the other: a second plan request that arrives while the
    # first still asks Apple then finds the answer in the cache.
    with _APPLE_VIEW_LOCK:
        hit = server.apple_cache.get(adsid)
        if fresh or hit is None or time.monotonic() - hit[0] > APPLE_CACHE_TTL:
            api = _api(adsid or None)
            teams = api.list_teams()
            remember_teams(adsid, teams)
            hit = (time.monotonic(), api, teams, {})
            server.apple_cache[adsid] = hit
        _at, api, teams, per_team = hit
        team = pick_team(teams, team_id)
        if team.team_id not in per_team:
            per_team[team.team_id] = api.app_id_overview(team.team_id)
        ids, quota = per_team[team.team_id]
    return adsid, team, Capabilities.for_team(team), ids, quota


async def _read_device_apps(job, udid: str | None = None) -> dict | None:
    """Installed user apps with their metadata - None without a device."""
    from .device.connection import ServiceProvider
    from .device.install import list_apps

    async def read():
        async with ServiceProvider(udid) as sp:
            return await list_apps(sp)
    try:
        return await job.isolated(read)
    except Exception:
        return None


def _slots(apps: dict | None, max_apps: int | None, replacing: str = "") -> dict | None:
    """The free profile's app slots on the iPhone: developer-signed apps
    count. The app being replaced does not take a second one."""
    from .device.install import app_origin
    if apps is None:
        return None
    used = [{"bundleId": b, "name": _app_name(b, m)}
            for b, m in apps.items()
            if app_origin(m)["developerSigned"] and b.lower() != replacing.lower()]
    return {"max": max_apps, "used": len(used),
            "apps": sorted(used, key=lambda a: a["name"].lower())}


def _quota_dict(q) -> dict:
    return {"maximum": q.maximum, "available": q.available,
            "nextFreeAt": q.next_free_at, "returnsAt": q.returns_at}


@method("install.plan")
async def _install_plan(server: Server, job: Job, params: dict):
    """What an install with the editor's choices would cost - for the live
    preview. Nothing is created."""
    from .errors import SigningError
    from .plan import QuotaExhausted, make_plan, resolve_keep, spare_candidates
    from .provisioning import derive_bundle_id
    from .quota import team_quota
    from .signing.ipa import inspect
    from .state import appid_log, store

    info = await asyncio.to_thread(inspect, Path(_need(params, "path")))
    apps = await _read_device_apps(job, _udid_param(params))
    protected = {r.bundle_id for r in store.all_installs()} | set(apps or {})

    def run():
        adsid, team, caps, ids, quota = _apple_view(
            server, _account_param(params), params.get("teamId"),
            fresh=bool(params.get("refresh")))
        keep = resolve_keep(info, _keep_param(params), caps.is_free)
        kwargs = dict(team_id=team.team_id, app_ids=ids, quota=quota, keep=keep,
                      bundle_id=_text_param(params, "bundleId"),
                      spare=_text_param(params, "spareAppId"),
                      protected=protected)
        error = None
        try:
            plan = make_plan(info, is_free=caps.is_free, **kwargs)
        except QuotaExhausted as exc:
            error = str(exc)
            plan = make_plan(info, is_free=False, **kwargs)   # still show it
        q = team_quota(caps.is_free, ids, quota, appid_log.times(team.team_id))
        return {
            "teamId": team.team_id, "teamName": team.name, "isFree": caps.is_free,
            "defaultBundleId": derive_bundle_id(info.bundle_id, team.team_id),
            "mainId": plan.main_id, "spare": plan.spare,
            "keep": keep,
            "extensions": [{"path": p, "identifier": i} for p, i in plan.extensions],
            "newAppIds": plan.new_app_ids, "notes": plan.notes, "error": error,
            "quota": _quota_dict(q),
            "spares": [{"identifier": a.identifier, "appIdId": a.app_id_id,
                        "expiresAt": a.expires_at.timestamp() if a.expires_at else None}
                       for a in spare_candidates(ids, protected)],
            "slots": _slots(apps, caps.max_apps_per_device, plan.main_id),
        }

    try:
        return await asyncio.to_thread(run)
    except SigningError as exc:
        raise RpcError(INVALID_PARAMS, str(exc)) from exc


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
    udid = _udid_param(params)

    async def run():
        async with ServiceProvider(udid) as sp:
            return await uninstall_app(sp, bundle_id)

    transport = await job.isolated(run)
    return {"transport": transport, "forgotten": store.forget(bundle_id)}


@method("jit")
async def _jit(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider
    from .device.jit import enable_jit

    bundle_id = _need(params, "bundleId")
    udid = _udid_param(params)

    async def run():
        async with ServiceProvider(udid) as sp:
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


def _account_dict(session, active: str | None) -> dict:
    return {"adsid": session.adsid, "appleId": session.apple_id,
            "firstName": session.first_name, "label": session.label,
            "active": session.adsid == active}


def _look_up_first_name(server: Server, adsid: str) -> None:
    """Fills in the greeting's first name for a session from before it
    existed - once per account and server, in the background.

    The status is polled every few seconds and must stay fast, so it only
    starts this; the next poll then carries the name. A failure (no
    network, Apple busy) is fine: the dashboard just says "Signed in", and
    the account page tries again.
    """
    if adsid in server.name_lookups:
        return
    server.name_lookups.add(adsid)

    def look_up() -> None:
        from .apple.session import remember_first_name
        try:
            remember_first_name(_api(adsid).list_teams(), adsid)
        except Exception:
            pass

    task = asyncio.get_running_loop().create_task(asyncio.to_thread(look_up))
    server._tasks.add(task)
    task.add_done_callback(server._tasks.discard)


def _account_param(params: dict) -> str | None:
    """The optional ``account`` (adsid) a call is about - else the active
    one."""
    value = params.get("account")
    return value if isinstance(value, str) and value else None


def _api(adsid: str | None = None):
    from .apple.devservices import DeveloperServices
    from .apple.session import Session
    from .errors import AppleError
    session = Session.load(adsid)
    if session is None:
        raise AppleError(_("Not signed in."))
    return DeveloperServices(session, _anisette())


@method("login")
async def _login(server: Server, job: Job, params: dict):
    from .apple.devservices import DeveloperServices
    from .apple.session import login, remember_teams

    apple_id = _need(params, "appleId").strip()
    password = _need(params, "password")

    def prompt_code() -> str:
        # With several accounts the code dialog has to say whose code it is.
        return server.ask_blocking("prompt.2fa", {"appleId": apple_id}) or ""

    def run():
        job.log("Preparing Anisette …")
        ani = _anisette()
        job.log("Signing in to Apple …")
        session = login(apple_id, password, ani, code_prompt=prompt_code)
        teams = DeveloperServices(session, ani).list_teams()
        remember_teams(session.adsid, teams)
        return [str(t) for t in teams]

    return {"teams": await asyncio.to_thread(run)}


@method("logout")
async def _logout(server: Server, job: Job, params: dict):
    from .apple.session import Session, active_adsid, list_accounts
    from .errors import AppleError
    adsid = _account_param(params) or active_adsid()
    forget = bool(params.get("forgetDevice"))
    # The device identity is shared by every account: discarding it would
    # force a new two-factor code on all the others as well.
    if forget and any(a.adsid != adsid for a in list_accounts()):
        raise AppleError(_("The device identity can only be discarded "
                           "together with the last account."))
    Session.clear(adsid)
    if forget:
        from .apple.anisette import DEVICE_FILE, PROVISIONING_FILE
        for f in (PROVISIONING_FILE, DEVICE_FILE):
            f.unlink(missing_ok=True)
    return True


@method("accounts.list")
async def _accounts_list(server: Server, job: Job, params: dict):
    from .apple.session import active_adsid, list_accounts
    active = active_adsid()
    return [_account_dict(a, active) for a in list_accounts()]


@method("accounts.setActive")
async def _accounts_set_active(server: Server, job: Job, params: dict):
    """Picks the account new installs sign with. Renewals don't care: they
    always use the account that owns the app's team."""
    from .apple.session import set_active
    set_active(_need(params, "adsid"))
    return True


@method("account")
async def _account(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider
    from .device.install import app_origin, list_apps
    from .provisioning import Capabilities, app_id_in_use
    from .quota import team_quota
    from .state import appid_log, store

    # An App ID is not only taken by what ModStaller installed: an app from
    # another tool can just as well depend on it. Without the device, "free"
    # would appear next to an App ID whose deletion breaks a working app.
    # But the iPhone is not always there - then we would rather say so than
    # guess (``usageKnown``).
    protected = {r.bundle_id for r in store.all_installs()}
    usage_known = False
    try:
        async def read():
            async with ServiceProvider(_udid_param(params)) as sp:
                return await list_apps(sp)

        apps = await job.isolated(read)
        protected |= {b for b, m in apps.items() if app_origin(m)["sideloaded"]}
        usage_known = True
    except Exception:
        apps = None     # No iPhone plugged in - the account page stays usable.

    from .apple.session import active_adsid
    adsid = _account_param(params) or active_adsid()

    def run():
        from .apple.session import remember_first_name, remember_teams
        api = _api(adsid)
        teams = api.list_teams()
        remember_teams(adsid, teams)
        remember_first_name(teams, adsid)
        out = []
        for team in teams:
            caps = Capabilities.for_team(team)
            app_ids, quota = api.app_id_overview(team.team_id)
            q = team_quota(caps.is_free, app_ids, quota,
                           appid_log.times(team.team_id))
            out.append({
                "teamId": team.team_id, "name": team.name, "type": team.type,
                "isFree": caps.is_free, "description": caps.describe(),
                "devices": len(api.list_devices(team.team_id)),
                "appIds": [{"appIdId": a.app_id_id, "identifier": a.identifier,
                            "name": a.name,
                            "inUse": app_id_in_use(a.identifier, protected),
                            "expiresAt": (a.expires_at.timestamp()
                                          if a.expires_at else None)}
                           for a in app_ids],
                "usageKnown": usage_known,
                "maxAppIdsPerWeek": caps.max_app_ids_per_week,
                "maxAppsPerDevice": caps.max_apps_per_device,
                "quota": _quota_dict(q),
                "slots": _slots(apps, caps.max_apps_per_device),
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
        api = _api(_account_param(params))
        team = pick_team(api.list_teams(), params.get("teamId"))
        api.delete_app_id(team.team_id, app_id_id)

    await asyncio.to_thread(run)
    server.apple_cache.clear()
    return True


def _cert_dict(c) -> dict:
    return {"certId": c.cert_id, "serial": c.serial, "name": c.name,
            "machineId": c.machine_id,
            "expiresAt": c.expires_at.isoformat() if c.expires_at else None}


@method("certs.list")
async def _certs_list(server: Server, job: Job, params: dict):
    from .provisioning import pick_team

    def run():
        api = _api(_account_param(params))
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
        api = _api(_account_param(params))
        team = pick_team(api.list_teams(), params.get("teamId"))
        api.revoke_certificate(team.team_id, serial)

    await asyncio.to_thread(run)
    return True


@method("device.info")
async def _device_info(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider, device_info
    udid = _udid_param(params)

    async def run():
        # Isolated: for an Apple TV this builds a tunnel, which takes a while.
        async with ServiceProvider(udid) as sp:
            return await device_info(sp.lockdown, sp.transport)

    info = await job.isolated(run)
    return {"udid": info.udid, "name": info.name,
            "productType": info.product_type, "iosVersion": info.ios_version,
            "build": info.build, "developerMode": info.developer_mode,
            "platform": info.platform, "transport": info.transport}


@method("device.apps")
async def _device_apps(server: Server, job: Job, params: dict):
    from .device.connection import ServiceProvider
    from .device.install import app_origin, list_apps

    async def run():
        async with ServiceProvider(_udid_param(params)) as sp:
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

    udid = _udid_param(params)

    async def run():
        async with ServiceProvider(udid) as sp:
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
    udid = _udid_param(params)
    return [asdict(c) for c in await job.isolated(lambda: run_checks(udid))]


@method("device.fix")
async def _device_fix(server: Server, job: Job, params: dict):
    from .device.readiness import run_fix
    fix = _need(params, "fix")
    udid = _udid_param(params)
    result = await job.isolated(lambda: run_fix(fix, udid, on_step=job.log))
    # Developer Mode & co. live in the status cache - it is now outdated.
    server.device_cache.clear()
    return asdict(result)


@method("device.wifi")
async def _device_wifi(server: Server, job: Job, params: dict):
    """Switches Wi-Fi for an iPhone on (needs the cable once) or off."""
    from .device import wifi
    udid = _udid_param(params)
    if params.get("enable"):
        result = await job.isolated(lambda: wifi.enable(udid, on_step=job.log))
    else:
        if udid is None:
            raise RpcError(INVALID_PARAMS, _("Parameter {key!r} is missing", key="udid"))
        result = await job.isolated(lambda: wifi.disable(udid, on_step=job.log))
    server.device_cache.clear()
    return result


@method("pair.browse")
async def _pair_browse(server: Server, job: Job, params: dict):
    """Apple TVs showing the pairing screen right now."""
    from .device import tvpair
    return await job.isolated(tvpair.browse)


@method("pair.start")
async def _pair_start(server: Server, job: Job, params: dict):
    """Pairs an Apple TV. The PIN it shows comes from the interface
    (``prompt.pin``)."""
    from .device import tvpair
    identifier = _need(params, "identifier")
    host = _need(params, "host")
    port = params.get("port")
    if not isinstance(port, int) or not 0 < port < 65536:
        raise RpcError(INVALID_PARAMS, _("Parameter {key!r} is missing", key="port"))
    name = _text_param(params, "name") or ""

    async def ask_pin(device_name: str) -> str | None:
        answer = await asyncio.to_thread(
            server.ask_blocking, "prompt.pin", {"name": device_name})
        return str(answer).strip() if answer else None

    dev = await job.isolated(lambda: tvpair.pair(
        identifier, host, port, name=name, ask_pin=ask_pin, on_step=job.log))
    server.device_cache.clear()
    return {"udid": dev.udid, "name": dev.name, "productType": dev.product_type,
            "osVersion": dev.os_version}


@method("devices.known")
async def _devices_known(server: Server, job: Job, params: dict):
    """Every device ModStaller remembers - also those not reachable now."""
    from .device import registry
    from .device.models import form_factor, marketing_name
    return [{"udid": d.udid, "name": d.name, "productType": d.product_type,
             "model": marketing_name(d.product_type) if d.product_type else "",
             "formFactor": form_factor(d.product_type) if d.product_type else "island",
             "platform": d.platform, "osVersion": d.os_version,
             "wifiEnabled": d.wifi_enabled, "paired": bool(d.remote_identifier),
             "lastSeen": d.last_seen}
            for d in registry.all_devices()]


@method("device.forget")
async def _device_forget(server: Server, job: Job, params: dict):
    """Forgets a device: Wi-Fi pairing, RemotePairing record, the entry."""
    from .device import discovery, registry
    udid = _need(params, "udid")
    known = registry.get(udid)
    if known is not None and known.remote_identifier:
        from pymobiledevice3.common import get_home_folder
        from pymobiledevice3.pair_records import get_remote_pairing_record_filename
        name = get_remote_pairing_record_filename(known.remote_identifier)
        for path in get_home_folder().glob(f"{name}.*"):
            path.unlink(missing_ok=True)
    forgotten = registry.forget(udid)
    if discovery.SCANNER is not None:
        discovery.SCANNER.forget(udid)
    server.device_cache.pop(udid, None)
    return {"forgotten": forgotten}


def _usb_setup_message(how: str) -> str:
    return {
        "already": _("The Apple device service is already running."),
        "started": _("The Apple device service was started."),
        "apple-devices": _("“Apple Devices” is installed - the Apple device "
                           "service runs."),
        "driver": _("Apple's USB driver is installed - the Apple device "
                    "service runs."),
    }.get(how, how)


@method("usb.setup")
async def _usb_setup(server: Server, job: Job, params: dict):
    """Windows: installs or starts the Apple device service (winsetup)."""
    from . import winsetup
    how = await asyncio.to_thread(
        winsetup.setup, on_step=job.log, on_progress=job.progress)
    server.usb_service_probe = None
    return {"method": how, "message": _usb_setup_message(how)}


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
    # Devices in the network are looked for in the background - the status
    # must never wait for a Bonjour browse.
    from .device import discovery
    discovery.SCANNER = discovery.NetworkScanner()
    discovery.SCANNER.start()
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
