"""Kommandozeile. Enthaelt bewusst keine Logik - nur Argumente und Ausgabe."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from . import config
from .errors import ModStallerError


def _ok(label: str, detail: str = "") -> None:
    print(f"  \033[32m✓\033[0m {label:<22} {detail}")


def _fail(label: str, detail: str = "") -> None:
    print(f"  \033[31m✗\033[0m {label:<22} {detail}")


# --------------------------------------------------------------------------


def cmd_doctor(args) -> int:
    print("ModStaller - Systemcheck\n")
    problems = 0

    # usbmuxd ist socket-aktiviert; ohne Geraet laeuft kein Prozess. Das ist
    # kein Fehler, deshalb pruefen wir den Socket, nicht den Prozess.
    sock = Path("/var/run/usbmuxd")
    (_ok if sock.exists() else _fail)("usbmuxd-Socket", str(sock))
    problems += not sock.exists()

    for mod, label in (("pymobiledevice3", "pymobiledevice3"),
                       ("anisette", "anisette (lokal)"),
                       ("cryptography", "cryptography")):
        try:
            m = __import__(mod)
            _ok(label, getattr(m, "__version__", ""))
        except Exception as exc:
            _fail(label, str(exc))
            problems += 1

    zsign = shutil.which(config.Settings.load().zsign_path)
    if zsign:
        _ok("zsign", zsign)
    else:
        _fail("zsign", "fehlt - installieren mit: paru -S zsign-bin")
        problems += 1

    ca = config.GSA_CA_BUNDLE
    (_ok if ca.exists() else _fail)("Apple-CA-Bundle", str(ca))
    problems += not ca.exists()

    # Anisette ist das Nadeloehr fuer den Login - lieber hier merken.
    try:
        from .apple import clientinfo
        from .apple.anisette import LocalProvider
        ci = LocalProvider().client_info()
        if clientinfo.is_safe(ci):
            _ok("Anisette-Client-Info", "com.apple.akd (GSA-tauglich)")
        else:
            _fail("Anisette-Client-Info", f"wuerde HTTP 503 ausloesen: {ci}")
            problems += 1
    except Exception as exc:
        _fail("Anisette-Provider", str(exc))
        problems += 1

    devs = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True)
    serials = [s for s in devs.stdout.split() if s]
    if serials:
        _ok("iPhone erkannt", ", ".join(serials))
    else:
        _fail("iPhone erkannt", "keins angesteckt (fuer Installation noetig)")

    print()
    print("Alles bereit." if not problems else
          f"{problems} Punkt(e) zu klaeren, siehe oben.")
    return 0 if not problems else 1


async def _device_info(args) -> int:
    from .device.connection import ServiceProvider, device_info
    async with ServiceProvider(args.udid) as sp:
        info = await device_info(sp.lockdown)
        print(info)
        if not info.developer_mode:
            print("\n  Developer Mode ist aus. Auf dem iPhone unter\n"
                  "  Einstellungen > Datenschutz & Sicherheit > Entwicklermodus\n"
                  "  aktivieren, sonst startet keine sideloadete App.")
    return 0


async def _device_apps(args) -> int:
    from .device.connection import ServiceProvider
    from .device.install import list_apps
    async with ServiceProvider(args.udid) as sp:
        apps = await list_apps(sp)
        if not apps:
            print("Keine Nutzer-Apps gefunden.")
            return 0
        for bid, meta in sorted(apps.items()):
            print(f"  {meta.get('CFBundleDisplayName', bid):<34} {bid}")
        print(f"\n{len(apps)} App(s).")
    return 0


async def _install(args) -> int:
    from .device.connection import ServiceProvider
    from .device.install import install_ipa
    if not args.no_sign:
        print("Signieren ist noch nicht implementiert (Meilenstein M3).\n"
              "Eine bereits signierte IPA geht mit --no-sign.", file=sys.stderr)
        return 2

    last = [-1]

    def progress(pct: int) -> None:
        if pct != last[0]:
            last[0] = pct
            print(f"\r  Installation {pct:3d}%", end="", flush=True)

    async with ServiceProvider(args.udid) as sp:
        res = await install_ipa(sp, Path(args.ipa), progress=progress)
        print(f"\r  Installation fertig (Transport: {res.transport})")
    return 0


# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="modstaller",
        description="iOS-Sideloader fuer Linux: IPAs signieren und installieren.")
    p.add_argument("-u", "--udid", help="Zielgeraet (Default: das einzige)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Pruefen, ob alles Noetige da ist"
                   ).set_defaults(func=cmd_doctor)

    dev = sub.add_parser("device", help="Geraete-Infos")
    devsub = dev.add_subparsers(dest="subcmd", required=True)
    devsub.add_parser("info", help="Modell, iOS-Version, Developer Mode"
                      ).set_defaults(afunc=_device_info)
    devsub.add_parser("apps", help="Installierte Nutzer-Apps"
                      ).set_defaults(afunc=_device_apps)

    ins = sub.add_parser("install", help="IPA installieren")
    ins.add_argument("ipa", help="Pfad zur IPA")
    ins.add_argument("--no-sign", action="store_true",
                     help="IPA ist bereits signiert, nur installieren")
    ins.set_defaults(afunc=_install)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config.ensure_dirs()
    try:
        if hasattr(args, "afunc"):
            return asyncio.run(args.afunc(args))
        return args.func(args)
    except ModStallerError as exc:
        print(f"\nFehler: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
