"""System check: is everything there that ModStaller needs?

Returns data only. How it looks is up to the CLI and the interface.
"""

from __future__ import annotations

import shutil
import socket
from dataclasses import dataclass
from pathlib import Path

from . import config
from .i18n import _

#: A problem prevents operation. An open step is not a fault of the system
#: but must stay visible (signing in, plugging in the iPhone).
PROBLEM, TODO = "problem", "todo"


@dataclass
class Check:
    label: str
    ok: bool
    detail: str = ""
    #: What to do when ``ok == False``.
    hint: str = ""
    kind: str = PROBLEM


#: Where the Apple device service listens on Windows (usbmuxd protocol).
APPLE_MOBILE_DEVICE = ("127.0.0.1", 27015)


def _usb_service_check(posix: bool = config.POSIX) -> Check:
    """The service through which the iPhone is reachable over USB."""
    if not posix:
        # On Windows pymobiledevice3 talks to the Apple device service over
        # TCP. It runs permanently once installed.
        try:
            socket.create_connection(APPLE_MOBILE_DEVICE, timeout=1).close()
            return Check(_("Apple device service"), True, _("running"))
        except OSError:
            return Check(
                _("Apple device service"), False, _("not reachable"),
                hint=_("Install the “Apple Devices” app from the Microsoft "
                       "Store (or iTunes) - it brings the service along."))

    # usbmuxd only starts when a device is plugged in (udev or socket
    # activation). Without an iPhone the socket is rightly missing - then
    # what counts is whether the program is installed at all.
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


#: Label of the JIT engine check - the packaging smoke test looks for it.
JIT_ENGINE = "JIT engine (QuickJS)"


def _jit_engine_check() -> Check:
    """QuickJS and our side of the JIT protocol - both have to be bundled.

    Loading the script also catches a syntax error before a user sits in
    front of a waiting app.
    """
    from importlib.metadata import PackageNotFoundError, version

    from .device.jit import HOST_SCRIPT
    try:
        import quickjs
        quickjs.Context().eval(HOST_SCRIPT.read_text(encoding="utf-8"))
    except Exception as exc:
        return Check(JIT_ENGINE, False, str(exc).splitlines()[0])
    try:
        ver = version("quickjs-ng")
    except PackageNotFoundError:
        ver = ""
    return Check(JIT_ENGINE, True, ver)


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

    checks.append(_jit_engine_check())

    settings = config.Settings.load()

    zsign = config.find_zsign(settings.zsign_path)
    checks.append(Check(
        "zsign", bool(zsign), zsign or _("missing"),
        hint=(_("install it with: paru -S zsign-bin") if config.POSIX
              else _("zsign.exe is missing - reinstall ModStaller."))))

    ca = config.GSA_CA_BUNDLE
    checks.append(Check(_("Apple CA bundle"), ca.exists(), str(ca)))

    # Anisette is the bottleneck for login - better to notice it here. Which
    # source applies is set in the settings, not here; the label names it so
    # the check doesn't hide where the identifiers go.
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
