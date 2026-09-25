"""Systemcheck: ist alles da, was ModStaller braucht?

Liefert nur Daten. Wie sie aussehen, entscheiden CLI und Oberflaeche.
"""

from __future__ import annotations

import shutil
import socket
from dataclasses import dataclass
from pathlib import Path

from . import config
from .i18n import _

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


#: Wo der Apple-Geraetedienst unter Windows lauscht (usbmuxd-Protokoll).
APPLE_MOBILE_DEVICE = ("127.0.0.1", 27015)


def _usb_service_check(posix: bool = config.POSIX) -> Check:
    """Der Dienst, ueber den das iPhone per USB erreichbar ist."""
    if not posix:
        # Unter Windows spricht pymobiledevice3 den Apple-Geraetedienst
        # ueber TCP an. Er laeuft dauerhaft, sobald er installiert ist.
        try:
            socket.create_connection(APPLE_MOBILE_DEVICE, timeout=1).close()
            return Check(_("Apple device service"), True, _("running"))
        except OSError:
            return Check(
                _("Apple device service"), False, _("not reachable"),
                hint=_("Install the “Apple Devices” app from the Microsoft "
                       "Store (or iTunes) - it brings the service along."))

    # usbmuxd startet erst, wenn ein Geraet angesteckt wird (udev bzw.
    # Socket-Aktivierung). Ohne iPhone fehlt der Socket also zu Recht - dann
    # zaehlt, ob das Programm ueberhaupt installiert ist.
    sock = Path("/var/run/usbmuxd")
    daemon = (shutil.which("usbmuxd")
              or next((p for p in ("/usr/bin/usbmuxd", "/usr/sbin/usbmuxd")
                       if Path(p).exists()), None))
    if sock.exists():
        return Check("usbmuxd", True, _("running ({socket})", socket=sock))
    return Check(
        "usbmuxd", bool(daemon),
        _("installed ({path}), starts when a device is plugged in",
          path=daemon) if daemon else _("not installed"),
        hint="Arch: sudo pacman -S usbmuxd - Debian/Ubuntu: sudo apt "
             "install usbmuxd - Fedora: sudo dnf install usbmuxd")


async def run_checks() -> list[Check]:
    checks: list[Check] = []

    checks.append(_usb_service_check())

    from importlib.metadata import PackageNotFoundError, version
    for mod, label in (("pymobiledevice3", "pymobiledevice3"),
                       ("anisette", "anisette (local)"),
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

    settings = config.Settings.load()

    zsign = config.find_zsign(settings.zsign_path)
    checks.append(Check(
        "zsign", bool(zsign), zsign or _("missing"),
        hint=(_("install it with: paru -S zsign-bin") if config.POSIX
              else _("zsign.exe is missing - reinstall ModStaller."))))

    ca = config.GSA_CA_BUNDLE
    checks.append(Check(_("Apple CA bundle"), ca.exists(), str(ca)))

    # Anisette ist das Nadeloehr fuer den Login - lieber hier merken. Welche
    # Quelle zaehlt, steht in den Einstellungen und nicht hier; das Label nennt
    # sie, damit der Check nicht verschweigt, wohin die Identifier gehen.
    label = (_("Anisette (local)") if settings.anisette_provider == "local"
             else _("Anisette (server: {url})",
                    url=settings.anisette_server))
    try:
        from .apple import anisette as anisette_mod
        from .apple import clientinfo
        ani = anisette_mod.build(settings.anisette_provider,
                                 settings.anisette_server)
        ci = ani.client_info()
        if clientinfo.is_safe(ci):
            checks.append(Check(label, True,
                                _("com.apple.akd (accepted by GSA)")))
        else:
            checks.append(Check(label, False,
                                _("would trigger HTTP 503: {info}", info=ci)))
    except Exception as exc:
        checks.append(Check(label, False, str(exc)))

    from .apple.session import Session
    logged_in = Session.load() is not None
    checks.append(Check(
        _("Apple sign-in"), logged_in,
        _("active") if logged_in else _("missing"),
        hint="modstaller login", kind=TODO))

    from .device.connection import list_devices
    serials = await list_devices()
    checks.append(Check(
        _("iPhone detected"), bool(serials),
        ", ".join(serials) if serials else _("none connected"),
        hint=_("Connect the iPhone via USB and unlock it"), kind=TODO))

    return checks


def problems(checks: list[Check]) -> list[Check]:
    return [c for c in checks if not c.ok and c.kind == PROBLEM]


def todos(checks: list[Check]) -> list[Check]:
    return [c for c in checks if not c.ok and c.kind == TODO]
