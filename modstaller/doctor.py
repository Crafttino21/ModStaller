"""Systemcheck: ist alles da, was ModStaller braucht?

Liefert nur Daten. Wie sie aussehen, entscheiden CLI und Oberflaeche.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from . import config

#: Ein Problem verhindert den Betrieb. Ein offener Schritt ist kein Fehler
#: des Systems, muss aber sichtbar bleiben (Anmeldung, iPhone anstecken).
PROBLEM, TODO = "problem", "todo"


@dataclass
class Check:
    label: str
    ok: bool
    detail: str = ""
    #: Was bei ``ok == False`` zu tun ist.
    hint: str = ""
    kind: str = PROBLEM


async def run_checks() -> list[Check]:
    checks: list[Check] = []

    # usbmuxd startet erst, wenn ein Geraet angesteckt wird (udev bzw.
    # Socket-Aktivierung). Ohne iPhone fehlt der Socket also zu Recht - dann
    # zaehlt, ob das Programm ueberhaupt installiert ist.
    sock = Path("/var/run/usbmuxd")
    daemon = (shutil.which("usbmuxd")
              or next((p for p in ("/usr/bin/usbmuxd", "/usr/sbin/usbmuxd")
                       if Path(p).exists()), None))
    if sock.exists():
        checks.append(Check("usbmuxd", True, f"laeuft ({sock})"))
    else:
        checks.append(Check(
            "usbmuxd", bool(daemon),
            f"installiert ({daemon}), startet beim Anstecken" if daemon
            else "nicht installiert",
            hint="Arch: sudo pacman -S usbmuxd - Debian/Ubuntu: sudo apt "
                 "install usbmuxd - Fedora: sudo dnf install usbmuxd"))

    from importlib.metadata import PackageNotFoundError, version
    for mod, label in (("pymobiledevice3", "pymobiledevice3"),
                       ("anisette", "anisette (lokal)"),
                       ("cryptography", "cryptography")):
        try:
            m = __import__(mod)
        except Exception as exc:
            checks.append(Check(label, False, str(exc)))
            continue
        try:
            ver = version(mod)
        except PackageNotFoundError:
            ver = getattr(m, "__version__", "")
        checks.append(Check(label, True, ver))

    zsign = shutil.which(config.Settings.load().zsign_path)
    checks.append(Check(
        "zsign", bool(zsign), zsign or "fehlt",
        hint="installieren mit: paru -S zsign-bin"))

    ca = config.GSA_CA_BUNDLE
    checks.append(Check("Apple-CA-Bundle", ca.exists(), str(ca)))

    # Anisette ist das Nadeloehr fuer den Login - lieber hier merken.
    try:
        from .apple import clientinfo
        from .apple.anisette import LocalProvider
        ci = LocalProvider().client_info()
        if clientinfo.is_safe(ci):
            checks.append(Check("Anisette-Client-Info", True,
                                "com.apple.akd (GSA-tauglich)"))
        else:
            checks.append(Check("Anisette-Client-Info", False,
                                f"wuerde HTTP 503 ausloesen: {ci}"))
    except Exception as exc:
        checks.append(Check("Anisette-Provider", False, str(exc)))

    from .apple.session import Session
    logged_in = Session.load() is not None
    checks.append(Check(
        "Apple-Anmeldung", logged_in, "aktiv" if logged_in else "fehlt",
        hint="modstaller login", kind=TODO))

    from .device.connection import list_devices
    serials = await list_devices()
    checks.append(Check(
        "iPhone erkannt", bool(serials),
        ", ".join(serials) if serials else "keins angesteckt",
        hint="iPhone per USB anstecken und entsperren", kind=TODO))

    return checks


def problems(checks: list[Check]) -> list[Check]:
    return [c for c in checks if not c.ok and c.kind == PROBLEM]


def todos(checks: list[Check]) -> list[Check]:
    return [c for c in checks if not c.ok and c.kind == TODO]
