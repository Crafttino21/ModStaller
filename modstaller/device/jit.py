"""JIT freischalten - auch auf iOS 26 und 27.

Bis iOS 18 genuegte es, einen Debugger anzuhaengen: der Kernel setzt dann
``CS_DEBUGGED``, und der Prozess darf Speicher ausfuehrbar machen. Das
ueberlebte das Loesen des Debuggers.

Auf Geraeten mit TXM/SPTM - allen neueren iPhones - reicht das nicht mehr.
Dort kann eine Seite nur noch ausfuehrbar werden, wenn ein *angehaengter*
Debugger von aussen hineinschreibt: ein Byte je 16-KB-Seite, und genau dieser
Zugriff erteilt das Recht.

Damit ist JIT keine einmalige Freischaltung mehr, sondern ein Gespraech. Die
App bittet ueber einen Haltepunkt (``brk #0xf00d``) um Vorbereitung einzelner
Bereiche; der Befehl steht in ``x16``, Adresse und Laenge in ``x0``/``x1``.
Der Debugger bereitet vor, traegt die Adresse in ``x0`` ein und laesst
weiterlaufen - bis die App sich abmeldet.

**Die App muss mitspielen.** Wer diesen Haltepunkt nicht auslöst, bekommt
auch kein JIT, egal welcher Debugger anhaengt. Amethyst bringt die
Unterstuetzung mit (``UniversalJIT26.js`` im Bundle).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from ..errors import DeviceError
from ..i18n import _
from .gdb import REG_PC, REG_X0, REG_X1, REG_X16, GdbClient

#: Der Debugger-Dienst hinter dem RSD-Tunnel (iOS 17+).
DEBUGPROXY = "com.apple.internal.dt.remote.debugproxy"

#: Der Haltepunkt, mit dem eine App um JIT bittet.
BRK_JIT = 0xF00D
#: Aeltere Haltepunkte, die noch vorkommen.
BRK_SCRIPT = 0x68
BRK_LEGACY = 0x69

#: Befehle in x16.
CMD_DETACH = 0
CMD_PREPARE_REGION = 1
CMD_NEW_BREAKPOINTS = 2
CMD_SET_DETACH_AFTER_FIRST = 3
CMD_PREPARE_FOR_PATCHING = 4

#: Groesste Menge, die wir in einem Paket lesen oder schreiben.
_CHUNK = 4096

#: Seitengroesse. Je Seite genuegt ein Byte-Zugriff.
PAGE_SIZE = 16 * 1024

#: Muster einer ARM64-BRK-Instruktion.
_BRK_MASK = 0xFFE0001F
_BRK_OPCODE = 0xD4200000

#: Wie lange wir auf die naechste Anfrage der App warten. Grosszuegig, weil
#: die App erst beim Start einer Instanz nach JIT fragt - der Nutzer muss
#: dazwischen im Programm navigieren.
WAIT_FOR_APP = 300.0

#: Schutz gegen ein Programm, das endlos Haltepunkte ausloest.
MAX_BREAKPOINTS = 5000


@dataclass
class JitResult:
    bundle_id: str
    pid: int
    prepared_regions: int = 0
    prepared_bytes: int = 0
    detached_cleanly: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if not self.prepared_regions:
            return _("The debugger was attached, but the app did not request "
                     "any region.")
        mb = self.prepared_bytes / (1024 * 1024)
        return _("Released {count} memory region(s) ({size:.1f} MB).",
                 count=self.prepared_regions, size=mb)


def _is_brk(instruction: int) -> bool:
    return (instruction & _BRK_MASK) == _BRK_OPCODE


def _brk_immediate(instruction: int) -> int:
    return (instruction >> 5) & 0xFFFF


async def _prepare_region(gdb: GdbClient, address: int, size: int) -> int:
    """Erteilt einem Speicherbereich das Ausfuehrungsrecht.

    Auf TXM/SPTM-Geraeten geschieht das allein dadurch, dass der angehaengte
    Debugger in jede Seite schreibt. Wir lesen deshalb ein Byte und schreiben
    dasselbe Byte zurueck - der Inhalt bleibt unveraendert, das Recht wird
    erteilt.
    """
    written = 0
    for page in range(address, address + size, PAGE_SIZE):
        current = await gdb.read_memory(page, 1)
        await gdb.write_memory(page, current)
        written += 1
    return written


class Jit26Session:
    """Fuehrt das Gespraech mit der App, bis sie sich abmeldet."""

    def __init__(self, gdb: GdbClient, result: JitResult, on_step,
                 verbose: bool = False) -> None:
        self._gdb = gdb
        self._result = result
        self._say = on_step
        self._verbose = verbose
        self._detached = False
        #: Manche Apps lassen den Debugger nach der ersten Anfrage gehen.
        self._detach_after_first = False

    def _trace(self, message: str) -> None:
        if self._verbose:
            self._say(f"    {message}")

    async def run(self) -> None:
        handled = 0
        while not self._detached:
            if handled >= MAX_BREAKPOINTS:
                self._result.notes.append(_(
                    "Aborted: the app triggered an unusual number of "
                    "breakpoints."))
                return
            stop = await self._gdb.cont(timeout=WAIT_FOR_APP)
            if not stop.is_stop:
                self._result.notes.append(_(
                    "The app stopped reporting back - it probably just kept "
                    "running."))
                return
            handled += 1
            await self._handle(stop)

    async def _handle(self, stop) -> None:
        pc = stop.register(REG_PC)
        thread = stop.thread
        if pc is None or thread is None:
            return

        instruction = int.from_bytes(await self._gdb.read_memory(pc, 4),
                                     "little")
        self._trace(
            f"Halt bei pc=0x{pc:x} instr=0x{instruction:08x} "
            f"x0=0x{stop.register(REG_X0) or 0:x} "
            f"x1=0x{stop.register(REG_X1) or 0:x} "
            f"x16=0x{stop.register(REG_X16) or 0:x}")
        if not _is_brk(instruction):
            # Ein gewoehnliches Signal - unveraendert durchreichen, sonst
            # verschluckt der Debugger einen Absturz der App.
            if stop.signal:
                await self._gdb.cont_with_signal(stop.signal, thread)
            return

        immediate = _brk_immediate(instruction)
        self._trace(f"Haltepunkt 0x{immediate:x}")
        # Ueber den Haltepunkt hinwegsetzen, sonst haelt die App dort erneut.
        await self._gdb.set_register(REG_PC, pc + 4, thread)

        if immediate == BRK_JIT:
            await self._dispatch(stop, thread)
        elif immediate == BRK_LEGACY:
            await self._get_jit_mapping(stop, thread)
        elif immediate == BRK_SCRIPT:
            await self._accept_script(stop, thread)
        else:
            self._result.notes.append(
                f"Unbekannter Haltepunkt 0x{immediate:x} uebersprungen.")

    async def _dispatch(self, stop, thread: str) -> None:
        command = stop.register(REG_X16)
        if command == CMD_DETACH:
            self._say(_("The app is detaching - JIT is in place."))
            await self._gdb.detach()
            self._detached = True
            self._result.detached_cleanly = True
            return

        if command == CMD_PREPARE_REGION:
            address = stop.register(REG_X0) or 0
            size = stop.register(REG_X1) or 0
            if not size:
                return
            if address == 0:
                # Die App ueberlaesst dem Debugger die Wahl der Adresse.
                address = await self._gdb.allocate(size, "rx")
            pages = await _prepare_region(self._gdb, address, size)
            self._result.prepared_regions += 1
            self._result.prepared_bytes += size
            self._say(f"Bereich {self._result.prepared_regions}: "
                      f"{size // 1024} KB in {pages} Seiten freigegeben")
            await self._gdb.set_register(REG_X0, address, thread)
            return

        if command == CMD_NEW_BREAKPOINTS:
            await self._accept_script(stop, thread)
            return

        if command == CMD_SET_DETACH_AFTER_FIRST:
            self._detach_after_first = bool(stop.register(REG_X0))
            return

        if command == CMD_PREPARE_FOR_PATCHING:
            address = stop.register(REG_X0) or 0
            size = stop.register(REG_X1) or 0
            if address and size:
                await self._rewrite(address, size)
                self._say(_("{size} KB released for patching",
                            size=size // 1024))
            return

        self._result.notes.append(_("Skipped unknown command {command}.",
                                    command=command))

    async def _get_jit_mapping(self, stop, thread: str) -> None:
        """Der aeltere Weg, Speicher anzufordern (``brk #0x69``).

        Hier steht die *Groesse* in ``x0`` - nicht die Adresse. Wer das mit
        dem neueren Aufruf verwechselt, fordert einen Bereich an der Adresse
        "Groesse" an und bekommt Unsinn zurueck.
        """
        size = stop.register(REG_X0) or 0
        if not size:
            return
        address = await self._gdb.allocate(size, "rx")
        self._trace(f"0x{size:x} Byte angefordert -> 0x{address:x}")
        pages = await _prepare_region(self._gdb, address, size)
        self._result.prepared_regions += 1
        self._result.prepared_bytes += size
        self._say(f"Bereich {self._result.prepared_regions}: "
                  f"{size // 1024} KB in {pages} Seiten freigegeben")
        await self._gdb.set_register(REG_X0, address, thread)
        self._trace(f"x0 := 0x{address:x} zurueckgemeldet")

        if self._detach_after_first:
            self._say(_("The app lets the debugger go - JIT is in place."))
            await self._gdb.detach()
            self._detached = True
            self._result.detached_cleanly = True

    async def _accept_script(self, stop, thread: str) -> None:
        """Die App moechte den Debugger um eigene Befehle erweitern.

        Sie schickt dafuer ein JavaScript-Schnipsel. ModStaller fuehrt kein
        JavaScript aus - die Befehle, die dieses Schnipsel ueblicherweise
        nachruestet, sind hier fest eingebaut. Deshalb genuegt es, die
        Anfrage anzunehmen und weiterzumachen.
        """
        self._trace("The app offers a debugger extension")
        address = stop.register(REG_X0) or 0
        size = min(stop.register(REG_X1) or 0, _CHUNK)
        if address and size:
            try:
                raw = await self._gdb.read_memory(address, size)
                text = raw.split(b"\x00", 1)[0].decode("utf-8", "replace")
                self._result.notes.append(_(
                    "The app offered a debugger extension; the commands it "
                    "usually adds are built in here.")
                    + (_(" (detected: {text!r}…)", text=text[:60])
                       if text else ""))
            except Exception:
                pass

    async def _rewrite(self, address: int, size: int) -> None:
        """Liest einen Bereich und schreibt ihn unveraendert zurueck.

        Auch hier erteilt der Schreibzugriff des Debuggers das Recht - nur
        geht es diesmal um den ganzen Bereich, nicht um eine Seite je 16 KB.
        """
        offset = 0
        while offset < size:
            length = min(_CHUNK, size - offset)
            current = await self._gdb.read_memory(address + offset, length)
            await self._gdb.write_memory(address + offset, current)
            offset += length


async def enable_jit(sp, bundle_id: str, *,
                     on_step=lambda msg: None,
                     verbose: bool = False) -> JitResult:
    """Startet die App und begleitet sie, bis JIT steht."""
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.process_control import (
        ProcessControl,
    )

    from .readiness import mount_developer_image

    await mount_developer_image(sp.lockdown, on_step)

    rsd = await sp.rsd()

    on_step(_("Launching the app suspended …"))
    try:
        async with DvtProvider(rsd) as dvt, ProcessControl(dvt) as control:
            pid = await control.launch(bundle_id, kill_existing=True,
                                       start_suspended=True)
    except Exception as exc:
        raise DeviceError(_("{bundle_id} could not be launched: {error}",
                            bundle_id=bundle_id, error=exc)) from exc

    result = JitResult(bundle_id=bundle_id, pid=pid)

    try:
        port = rsd.get_service_port(DEBUGPROXY)
    except Exception as exc:
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

        on_step(_("Waiting for requests from the app … (start the instance "
                  "inside the app now)"))
        await Jit26Session(gdb, result, on_step, verbose=verbose).run()
    finally:
        try:
            if not result.detached_cleanly:
                await gdb.detach()
            await conn.close()
        except Exception:
            pass

    return result
