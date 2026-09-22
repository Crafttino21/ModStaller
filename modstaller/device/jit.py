"""JIT fuer eine sideloadete App freischalten.

iOS verbietet Programmen, zur Laufzeit Maschinencode zu erzeugen. Genau das
braucht aber jede Java- oder Emulator-App - ohne JIT bleiben sie beim Start
haengen ("Warte auf JIT").

Die Ausnahme: haengt ein Debugger am Prozess, setzt der Kernel ``CS_DEBUGGED``,
und dann darf er Speicher ausfuehrbar machen. Das ueberlebt das Loesen des
Debuggers. Der Ablauf ist deshalb: App angehalten starten, Debugger anhaengen,
sofort wieder loesen - die App laeuft weiter und darf jetzt kompilieren.

Vorausgesetzt ist die ``get-task-allow``-Berechtigung. Development-signierte
Apps haben sie; App-Store-Apps nicht, weshalb JIT dort nie funktioniert.

Ab iOS 17 liegt der Debugger-Dienst hinter dem RSD-Tunnel. Ueber den
Userspace-Tunnel ist die Geraeteadresse nur im eigenen Prozess erreichbar -
ein gewoehnlicher Socket kaeme nicht an, deshalb laeuft alles ueber die
Verbindung, die pymobiledevice3 selbst aufbaut.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..errors import DeviceError

#: Der Debugger-Dienst hinter dem RSD-Tunnel (iOS 17+).
DEBUGPROXY = "com.apple.internal.dt.remote.debugproxy"

#: Wie lange wir auf eine Antwort des Debuggers warten.
REPLY_TIMEOUT = 15.0


@dataclass
class JitResult:
    bundle_id: str
    pid: int


def _packet(payload: str) -> bytes:
    """Ein Paket im GDB-Remote-Protokoll: ``$<Inhalt>#<Pruefsumme>``."""
    checksum = sum(payload.encode()) & 0xFF
    return f"${payload}#{checksum:02x}".encode()


async def _read_packet(conn, timeout: float = REPLY_TIMEOUT) -> str:
    """Liest bis zum naechsten vollstaendigen Paket.

    Der Debugger schickt Empfangsbestaetigungen (``+``) getrennt vom
    eigentlichen Paket, teils in eigenen Segmenten. Wer nur einmal liest,
    haelt die Bestaetigung faelschlich fuer die Antwort - und meldet einen
    Fehlschlag, wo gerade alles funktioniert hat.
    """
    buffer = ""
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return buffer
        try:
            chunk = await asyncio.wait_for(conn.recv_any(), timeout=remaining)
        except asyncio.TimeoutError:
            return buffer
        if not chunk:
            return buffer
        buffer += chunk.decode("utf-8", "replace")

        start = buffer.find("$")
        if start < 0:
            continue  # bisher nur Bestaetigungen
        end = buffer.find("#", start)
        if end >= 0 and len(buffer) >= end + 3:
            return buffer[start:end + 3]


async def _exchange(conn, payload: str, *, expect_reply: bool = True) -> str:
    await conn.sendall(_packet(payload))
    if not expect_reply:
        return ""
    return await _read_packet(conn)


def _attached(reply: str) -> bool:
    """Hat sich der Debugger angehaengt?

    Der Debugger meldet den angehaltenen Zustand als ``T``- oder ``S``-Paket.
    Ein ``E`` ist eine Absage, Leeres ein Zeitablauf, ein blosses ``+`` nur
    die Empfangsbestaetigung - und damit noch keine Antwort.
    """
    body = reply.lstrip("+-$")
    return bool(body) and body[0] in ("T", "S")


async def enable_jit(sp, bundle_id: str, *,
                     on_step=lambda msg: None) -> JitResult:
    """Startet die App und schaltet JIT frei."""
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.process_control import (
        ProcessControl,
    )
    from pymobiledevice3.exceptions import (
        AlreadyMountedError, DeveloperDiskImageNotFoundError,
    )
    from pymobiledevice3.services.mobile_image_mounter import auto_mount

    # 1. Das Developer Disk Image traegt den Debugger-Dienst. Ohne das Abbild
    #    gibt es keinen Debugger, und ohne Debugger kein JIT.
    on_step("Developer Disk Image bereitstellen …")
    try:
        await auto_mount(sp.lockdown)
    except AlreadyMountedError:
        pass  # genau der Zustand, den wir wollten
    except DeveloperDiskImageNotFoundError as exc:
        raise DeviceError(
            "Kein passendes Developer Disk Image gefunden.\n"
            f"Fuer iOS-Versionen, die neuer sind als der Datenbestand von "
            f"pymobiledevice3, gibt es noch keins. ({exc})"
        ) from exc
    except Exception as exc:
        # Die Ausnahmen des Mounters tragen nicht immer einen Text - dann
        # sagt wenigstens der Typ, was passiert ist.
        detail = str(exc) or type(exc).__name__
        raise DeviceError(
            f"Developer Disk Image liess sich nicht laden: {detail}\n"
            "Ohne das Abbild gibt es keinen Debugger auf dem Geraet."
        ) from exc

    rsd = await sp.rsd()

    # 2. Angehalten starten: der Debugger soll sich anhaengen koennen, bevor
    #    die App ueberhaupt dazu kommt, JIT anzufordern.
    on_step("App angehalten starten …")
    try:
        async with DvtProvider(rsd) as dvt, ProcessControl(dvt) as control:
            pid = await control.launch(bundle_id, kill_existing=True,
                                       start_suspended=True)
    except Exception as exc:
        raise DeviceError(
            f"{bundle_id} liess sich nicht starten: {exc}\n"
            "Ist die App installiert und mit einem Entwickler-Zertifikat "
            "signiert?"
        ) from exc

    # 3. Anhaengen und sofort wieder loesen.
    on_step(f"Debugger anhaengen (Prozess {pid}) …")
    try:
        port = rsd.get_service_port(DEBUGPROXY)
    except Exception as exc:
        raise DeviceError(
            f"Der Debugger-Dienst ist nicht erreichbar: {exc}\n"
            "Das deutet darauf hin, dass das Developer Disk Image nicht "
            "geladen ist."
        ) from exc

    conn = await rsd.create_service_connection(port)
    try:
        # Ohne Bestaetigungen ist der Austausch unempfindlich gegen
        # Paket-Pruefsummen, die uns hier nichts nuetzen.
        await _exchange(conn, "QStartNoAckMode")
        await _exchange(conn, "QSetDetachOnError:1")

        reply = await _exchange(conn, f"vAttach;{pid:x}")
        if not _attached(reply):
            raise DeviceError(
                "Der Debugger konnte sich nicht an die App haengen "
                f"(Antwort: {reply.strip() or 'keine'}).\n"
                "Auf iOS 26 und 27 hat Apple die Freischaltung eingeschraenkt; "
                "sie gelingt dort nicht mehr fuer jede App."
            )

        # Loesen laesst die App weiterlaufen - die Markierung bleibt.
        await _exchange(conn, "D", expect_reply=False)
    finally:
        try:
            await conn.close()
        except Exception:
            pass

    on_step("JIT ist aktiv.")
    return JitResult(bundle_id=bundle_id, pid=pid)
