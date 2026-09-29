"""Enabling JIT - on iOS 26 and 27 too.

Up to iOS 18 it was enough to attach a debugger: the kernel then sets
``CS_DEBUGGED`` and the process may make memory executable. That survived
detaching the debugger - and on devices without TXM it still does.

On devices with TXM/SPTM - all newer iPhones - that is no longer enough.
There a page can only become executable if an *attached* debugger writes
into it from outside: one byte per 16 KB page, and exactly that access grants
the right.

So JIT is no longer a one-off unlock but a conversation. The app asks via a
breakpoint (``brk #0xf00d``) for individual regions to be prepared; the
command is in ``x16``, address and length in ``x0``/``x1``. The debugger
prepares them, puts the address into ``x0`` and lets the app continue -
until the app signs off.

The debugger side of that conversation is the "universal" protocol that
StikDebug established. Apps may extend it: they send a piece of JavaScript
(``brk #0x68``, or command 2) that registers commands of their own. That is
why our side is JavaScript too - ``jit_host.js``, run in QuickJS - so such
an extension really runs instead of being nodded through.

**The app has to play along.** An app that never triggers this breakpoint
gets no JIT on TXM devices, no matter which debugger is attached.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

from ..errors import DeviceError
from ..i18n import _
from .gdb import GdbClient
from .models import _numbers

log = logging.getLogger(__name__)

#: The debugger service behind the RSD tunnel (iOS 17+).
DEBUGPROXY = "com.apple.internal.dt.remote.debugproxy"

#: Our side of the protocol.
HOST_SCRIPT = Path(__file__).with_name("jit_host.js")

#: Page size. A single byte access per page is enough.
PAGE_SIZE = 16 * 1024

#: How long we wait for the app's next request. Generous, because the app
#: only asks for JIT when an instance is started - the user has to navigate
#: through the program in between.
WAIT_FOR_APP = 300.0

#: Guard against a program that triggers breakpoints endlessly.
MAX_BREAKPOINTS = 5000

#: Marks a failed host call for the script (see ``jit_host.js``).
_FAILED = "\x00"


@dataclass
class JitResult:
    bundle_id: str
    pid: int
    prepared_regions: int = 0
    prepared_bytes: int = 0
    detached_cleanly: bool = False
    #: Whether the device needed the conversation at all.
    txm: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if not self.txm:
            return _("JIT is in place - this device only needs the debugger "
                     "attached once.")
        if not self.prepared_regions:
            return _("The debugger was attached, but the app did not request "
                     "any region.")
        mb = self.prepared_bytes / (1024 * 1024)
        return _("Released {count} memory region(s) ({size:.1f} MB).",
                 count=self.prepared_regions, size=mb)


def has_txm(product_type: str, ios_version: str) -> bool:
    """Whether the device needs the conversation (as StikDebug decides it).

    TXM arrived with the A15 (iPhone14,2) and M2 iPads (iPad14,5) - but it
    only locks JIT down from iOS 26 on. From iOS 27 every supported device
    has it except the two iPad Pros that are still around.
    """
    try:
        major = int(ios_version.split(".")[0])
    except ValueError:
        return True             # unknown: rather talk than miss requests
    if major >= 27:
        return product_type not in ("iPad8,11", "iPad8,12")
    if major < 26:
        return False
    numbers = _numbers(product_type)
    if numbers is None:
        return True
    if product_type.startswith("iPad"):
        return numbers >= (14, 5)
    return numbers >= (14, 2)


async def touch_pages(gdb: GdbClient, address: int, size: int) -> int:
    """Grants a memory region the right to execute.

    On TXM/SPTM devices this happens solely by the attached debugger writing
    into every page. We read the first byte of every page and write the same
    byte back - the content stays unchanged, the right is granted. Both
    passes go out in batches; one round trip per page would take minutes
    for a large region.
    """
    pages = list(range(address, address + size, PAGE_SIZE))
    replies = await gdb.send_batch([f"m{page:x},1" for page in pages])
    for page, reply in zip(pages, replies):
        if len(reply) != 2 or reply.startswith("E"):
            raise DeviceError(_(
                "Memory at 0x{address:x} is not readable (reply: {reply!r})",
                address=page, reply=reply))
    replies = await gdb.send_batch(
        [f"M{page:x},1:{byte}" for page, byte in zip(pages, replies)])
    for page, reply in zip(pages, replies):
        if reply.startswith("E"):
            raise DeviceError(_(
                "Memory at 0x{address:x} is not writable (reply: {reply!r})",
                address=page, reply=reply))
    return len(pages)


class ScriptHost:
    """Runs ``jit_host.js`` and lends it the debugger connection.

    QuickJS calls are synchronous, the connection is async. So the script
    runs in a worker thread, and every call it makes is handed to the event
    loop and waited for there.
    """

    def __init__(self, gdb: GdbClient, result: JitResult, on_step, *,
                 txm: bool = True, verbose: bool = False) -> None:
        self._gdb = gdb
        self._result = result
        self._say = on_step
        self._txm = txm
        self._verbose = verbose
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop = threading.Event()
        #: The first failure of a host call - raised again once the script
        #: has unwound.
        self._error: BaseException | None = None

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        try:
            reason = await asyncio.to_thread(self._run_script)
        except BaseException:
            self._stop.set()
            raise
        if reason == "silent":
            self._result.notes.append(_(
                "The app stopped reporting back - it probably just kept "
                "running."))
        elif reason == "exited":
            self._result.notes.append(_(
                "The app quit while the debugger was attached."))
        elif reason == "limit":
            self._result.notes.append(_(
                "Aborted: the app triggered an unusual number of "
                "breakpoints."))

    def _run_script(self) -> str:
        import quickjs

        ctx = quickjs.Context()
        ctx.add_callable("__host_send", self._send)
        ctx.add_callable("__host_prepare", self._prepare)
        ctx.add_callable("__host_log", self._log)
        ctx.add_callable("__host_event", self._event)
        ctx.add_callable("__host_pid", lambda: self._result.pid)
        ctx.add_callable("__host_txm", lambda: self._txm)
        try:
            ctx.eval(HOST_SCRIPT.read_text(encoding="utf-8"))
            return str(ctx.eval(f"main({MAX_BREAKPOINTS})"))
        except quickjs.JSException as exc:
            if self._error is not None:
                raise self._error from None
            raise DeviceError(_("The JIT script failed: {error}",
                                error=str(exc).splitlines()[0])) from exc

    # -- Called from the script (worker thread). Never raise. ---------------

    def _await(self, coro):
        """Runs ``coro`` on the event loop and waits for it here."""
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        except RuntimeError:
            coro.close()
            raise
        while True:
            if self._stop.is_set():
                future.cancel()
                raise DeviceError(_("Stopped."))
            try:
                return future.result(timeout=0.25)
            except TimeoutError:
                continue

    def _failed(self, exc: BaseException) -> str:
        if self._error is None:
            self._error = exc
        return _FAILED + str(exc)

    def _send(self, payload: str) -> str:
        try:
            if payload == "D":
                self._await(self._gdb.send("D", expect_reply=False))
                if not self._result.detached_cleanly:
                    self._say(_("The app is detaching - JIT is in place."))
                self._result.detached_cleanly = True
                return ""
            waits = payload == "c" or payload.startswith("vCont")
            return self._await(self._gdb.send(
                payload, timeout=WAIT_FOR_APP if waits else None))
        except BaseException as exc:
            return self._failed(exc)

    def _prepare(self, address: str, size: str) -> str:
        try:
            address_, size_ = int(address), int(size)
            if not size_:
                return "OK"
            pages = self._await(touch_pages(self._gdb, address_, size_))
            self._result.prepared_regions += 1
            self._result.prepared_bytes += size_
            self._say(f"Region {self._result.prepared_regions}: "
                      f"{size_ // 1024} KB released in {pages} pages")
            return "OK"
        except BaseException as exc:
            return self._failed(exc)

    def _log(self, message: str) -> None:
        log.debug("jit: %s", message)
        if self._verbose:
            self._say(f"    {message}")

    def _event(self, kind: str, detail: str) -> None:
        if kind == "script":
            self._say(_("The app sent a debugger extension - it is active "
                        "now."))
        elif kind == "script_failed":
            self._result.notes.append(_(
                "The app's debugger extension failed: {error}",
                error=detail))
        elif kind == "unknown_command":
            self._result.notes.append(_("Skipped unknown command {command}.",
                                        command=detail))


async def enable_jit(sp, bundle_id: str, *,
                     on_step=lambda msg: None,
                     verbose: bool = False) -> JitResult:
    """Launches the app and stays with it until JIT is in place."""
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.process_control import (
        ProcessControl,
    )

    from .connection import device_info
    from .readiness import mount_developer_image

    info = await device_info(sp.lockdown, sp.transport)
    if info.platform == "tvos":
        # Needs a tvOS Developer Disk Image - pymobiledevice3 has none.
        raise DeviceError(_("JIT is not available for Apple TV yet."))
    txm = has_txm(info.product_type, info.ios_version)

    await mount_developer_image(sp, on_step)

    rsd = await sp.rsd()

    on_step(_("Launching the app suspended …"))
    try:
        async with DvtProvider(rsd) as dvt, ProcessControl(dvt) as control:
            pid = await control.launch(bundle_id, kill_existing=True,
                                       start_suspended=True)
    except Exception as exc:
        raise DeviceError(_("{bundle_id} could not be launched: {error}",
                            bundle_id=bundle_id, error=exc)) from exc

    result = JitResult(bundle_id=bundle_id, pid=pid, txm=txm)

    try:
        port = rsd.get_service_port(DEBUGPROXY)
    except Exception as exc:
        if DEBUGPROXY not in rsd.peer_info.get("Services", {}):
            # The image counts as mounted, but iOS never started its
            # services - seen after swapping images without a restart.
            raise DeviceError(_(
                "The Developer Disk Image is mounted, but the iPhone does "
                "not offer its debugger. Restart the iPhone and try again - "
                "ModStaller mounts the image anew.")) from exc
        raise DeviceError(_("The debugger service is not reachable: {error}",
                            error=exc)) from exc

    conn = await rsd.create_service_connection(port)
    gdb = GdbClient(conn)
    try:
        await gdb.start_no_ack_mode()
        on_step(_("Attaching the debugger (process {pid}) …", pid=pid))
        if not (await gdb.attach(pid)).is_stop:
            raise DeviceError(_(
                "The debugger could not attach to the app."))

        if not txm:
            # Attaching alone sets CS_DEBUGGED - and that outlasts the
            # debugger here.
            await gdb.detach()
            result.detached_cleanly = True
            on_step(result.summary)
            return result

        on_step(_("Waiting for requests from the app … (start the instance "
                  "inside the app now)"))
        await ScriptHost(gdb, result, on_step, txm=txm,
                         verbose=verbose).run()
    finally:
        try:
            if not result.detached_cleanly:
                await gdb.detach()
            await conn.close()
        except Exception:
            pass

    return result
