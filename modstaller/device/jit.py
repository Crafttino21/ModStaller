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
            return ("Der Debugger hing an, die App hat aber keinen Bereich "
                    "angefordert.")
        mb = self.prepared_bytes / (1024 * 1024)
        return (f"{self.prepared_regions} Speicherbereich(e) freigegeben "
                f"({mb:.1f} MB).")


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

    def __init__(self, gdb: GdbClient, result: JitResult, on_step) -> None:
        self._gdb = gdb
        self._result = result
        self._say = on_step
        self._detached = False

    async def run(self) -> None:
        handled = 0
        while not self._detached:
            if handled >= MAX_BREAKPOINTS:
                self._result.notes.append(
                    "Abbruch: die App hat ungewoehnlich viele Haltepunkte "
                    "ausgeloest.")
                return
            stop = await self._gdb.cont(timeout=WAIT_FOR_APP)
            if not stop.is_stop:
                self._result.notes.append(
                    "Die App hat sich nicht mehr gemeldet - vermutlich lief "
                    "sie einfach weiter.")
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
        if not _is_brk(instruction):
            # Ein gewoehnliches Signal - unveraendert durchreichen, sonst
            # verschluckt der Debugger einen Absturz der App.
            if stop.signal:
                await self._gdb.cont_with_signal(stop.signal, thread)
            return

        immediate = _brk_immediate(instruction)
        # Ueber den Haltepunkt hinwegsetzen, sonst haelt die App dort erneut.
        await self._gdb.set_register(REG_PC, pc + 4, thread)

        if immediate == BRK_JIT:
            await self._dispatch(stop, thread)
        elif immediate == BRK_LEGACY:
            # Alter Haltepunkt: als "nicht unterstuetzt" beantworten.
            await self._gdb.set_register(REG_X0, 0xE0000069, thread)
        elif immediate == BRK_SCRIPT:
            self._result.notes.append(
                "Die App wollte dem Debugger ein eigenes Skript unterschieben "
                "- das unterstuetzt ModStaller nicht.")
        else:
            self._result.notes.append(
                f"Unbekannter Haltepunkt 0x{immediate:x} uebersprungen.")

    async def _dispatch(self, stop, thread: str) -> None:
        command = stop.register(REG_X16)
        if command == CMD_DETACH:
            self._say("Die App meldet sich ab - JIT steht.")
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
            self._result.notes.append(
                "Die App wollte den Debugger um eigene Befehle erweitern - "
                "das unterstuetzt ModStaller nicht.")
            return

        self._result.notes.append(f"Unbekannter Befehl {command} uebersprungen.")


async def enable_jit(sp, bundle_id: str, *,
                     on_step=lambda msg: None) -> JitResult:
    """Startet die App und begleitet sie, bis JIT steht."""
    from pymobiledevice3.exceptions import (
        AlreadyMountedError, DeveloperDiskImageNotFoundError,
    )
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.process_control import (
        ProcessControl,
    )
    from pymobiledevice3.services.mobile_image_mounter import auto_mount

    on_step("Developer Disk Image bereitstellen …")
    try:
        await auto_mount(sp.lockdown)
    except AlreadyMountedError:
        pass
    except DeveloperDiskImageNotFoundError as exc:
        raise DeviceError(
            "Kein passendes Developer Disk Image gefunden - fuer sehr neue "
            f"iOS-Versionen gibt es noch keins. ({exc})"
        ) from exc
    except Exception as exc:
        raise DeviceError(
            f"Developer Disk Image liess sich nicht laden: "
            f"{exc or type(exc).__name__}"
        ) from exc

    rsd = await sp.rsd()

    on_step("App angehalten starten …")
    try:
        async with DvtProvider(rsd) as dvt, ProcessControl(dvt) as control:
            pid = await control.launch(bundle_id, kill_existing=True,
                                       start_suspended=True)
    except Exception as exc:
        raise DeviceError(
            f"{bundle_id} liess sich nicht starten: {exc}"
        ) from exc

    result = JitResult(bundle_id=bundle_id, pid=pid)

    try:
        port = rsd.get_service_port(DEBUGPROXY)
    except Exception as exc:
        raise DeviceError(
            f"Der Debugger-Dienst ist nicht erreichbar: {exc}"
        ) from exc

    conn = await rsd.create_service_connection(port)
    gdb = GdbClient(conn)
    try:
        await gdb.start_no_ack_mode()
        on_step(f"Debugger anhaengen (Prozess {pid}) …")
        if not (await gdb.attach(pid)).is_stop:
            raise DeviceError(
                "Der Debugger konnte sich nicht an die App haengen.")

        on_step("Warte auf Anfragen der App … (jetzt im Programm die "
                "Instanz starten)")
        await Jit26Session(gdb, result, on_step).run()
    finally:
        try:
            if not result.detached_cleanly:
                await gdb.detach()
            await conn.close()
        except Exception:
            pass

    return result
