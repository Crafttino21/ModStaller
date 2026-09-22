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


def _progress_printer():
    last = [-1]

    def progress(pct: int) -> None:
        if pct != last[0]:
            last[0] = pct
            print(f"\r  {pct:3d}%", end="", flush=True)

    return progress


# -- doctor ----------------------------------------------------------------


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

    # Die folgenden zwei sind keine Systemfehler, sondern offene Schritte -
    # sie zaehlen nicht als Problem, muessen aber sichtbar bleiben.
    todo = []

    from .apple.session import Session
    if Session.load():
        _ok("Apple-Anmeldung", "aktiv")
    else:
        _fail("Apple-Anmeldung", "fehlt")
        todo.append("modstaller login")

    devs = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True)
    serials = [x for x in devs.stdout.split() if x]
    if serials:
        _ok("iPhone erkannt", ", ".join(serials))
    else:
        _fail("iPhone erkannt", "keins angesteckt")
        todo.append("iPhone per USB anstecken und entsperren")

    print()
    if problems:
        print(f"{problems} Punkt(e) zu klaeren, siehe oben.")
    elif todo:
        print("System ist bereit. Noch offen:")
        for t in todo:
            print(f"  - {t}")
    else:
        print("Alles bereit.")
    return 1 if problems else 0


# -- Anmeldung -------------------------------------------------------------


def _anisette():
    from .apple import anisette as anisette_mod
    s = config.Settings.load()
    return anisette_mod.build(s.anisette_provider, s.anisette_server)


async def _login(args) -> int:
    import getpass
    from .apple.devservices import DeveloperServices
    from .apple.session import login

    apple_id = args.apple_id or input("Apple ID: ").strip()
    if not apple_id:
        print("Keine Apple ID angegeben.", file=sys.stderr)
        return 2
    password = getpass.getpass("Passwort (wird nicht gespeichert): ")

    print("\nAnisette vorbereiten …", flush=True)
    ani = _anisette()

    def prompt_code() -> str:
        return input("2FA-Code von deinem iPhone: ").strip()

    print("Bei Apple anmelden …", flush=True)
    session = login(apple_id, password, ani, code_prompt=prompt_code,
                    debug=args.debug)
    print("\nAngemeldet.")

    print("\nTeams:")
    for t in DeveloperServices(session, ani).list_teams():
        print(f"  {t}")
    return 0


def _logout(args) -> int:
    from .apple.session import Session
    Session.clear()
    print("Abgemeldet.")
    if args.forget_device:
        from .apple.anisette import DEVICE_FILE, PROVISIONING_FILE
        for f in (PROVISIONING_FILE, DEVICE_FILE):
            f.unlink(missing_ok=True)
        print("Geraete-Identitaet verworfen - beim naechsten Login fragt "
              "Apple wieder nach einem 2FA-Code.")
    return 0


async def _account(args) -> int:
    from .apple.devservices import DeveloperServices
    from .apple.session import Session
    from .provisioning import Capabilities

    session = Session.load()
    if session is None:
        print("Nicht angemeldet. Zuerst: modstaller login", file=sys.stderr)
        return 3

    ani = _anisette()
    api = DeveloperServices(session, ani)
    for t in api.list_teams():
        caps = Capabilities.for_team(t)
        print(t)
        print(f"  {caps.describe()}")
        print(f"  Geraete: {len(api.list_devices(t.team_id))}")
        app_ids = api.list_app_ids(t.team_id)
        if caps.max_app_ids_per_week:
            left = caps.max_app_ids_per_week - len(app_ids)
            note = (f" - noch {left} frei" if left > 0
                    else " - Kontingent ausgeschoepft, ModStaller recycelt "
                         "beim naechsten Installieren eine alte")
            print(f"  App-IDs: {len(app_ids)}/{caps.max_app_ids_per_week}{note}")
        else:
            print(f"  App-IDs: {len(app_ids)}")
        for a in app_ids:
            print(f"    {a.identifier}")
    return 0


async def _certs(args) -> int:
    from .apple.devservices import DeveloperServices
    from .apple.session import Session
    from .provisioning import pick_team

    session = Session.load()
    if session is None:
        print("Nicht angemeldet. Zuerst: modstaller login", file=sys.stderr)
        return 3
    ani = _anisette()
    api = DeveloperServices(session, ani)
    team = pick_team(api.list_teams(), args.team)
    certs = api.list_certificates(team.team_id)

    if args.revoke:
        match = [c for c in certs
                 if args.revoke in (c.cert_id, c.serial, c.name)]
        if not match:
            print(f"Kein Zertifikat mit {args.revoke!r} gefunden.",
                  file=sys.stderr)
            return 2
        cert = match[0]
        print(f"Widerrufen: {cert}")
        print("Apps, die damit signiert wurden, starten danach nicht mehr.")
        if not args.yes:
            if input("Wirklich widerrufen? [ja/NEIN] ").strip().lower() not in (
                    "ja", "j", "yes", "y"):
                print("Abgebrochen.")
                return 0
        api.revoke_certificate(team.team_id, cert.serial)
        print("Widerrufen.")
        return 0

    if not certs:
        print("Keine Development-Zertifikate im Account.")
        return 0
    print(f"{len(certs)} Development-Zertifikat(e):\n")
    for c in certs:
        print(f"  {c}")
    print("\nModStaller kann keins davon mitbenutzen - der private "
          "Schluessel\nliegt bei dem Werkzeug, das es angefordert hat.")
    return 0


# -- Geraet ----------------------------------------------------------------


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


# -- Installation ----------------------------------------------------------


async def _install(args) -> int:
    from .pipeline import install as run_install

    progress = _progress_printer()

    if args.no_sign:
        from .device.connection import ServiceProvider
        from .device.install import install_ipa
        async with ServiceProvider(args.udid) as sp:
            res = await install_ipa(sp, Path(args.ipa), progress=progress)
            print(f"\r  Installiert (Transport: {res.transport})")
        return 0

    outcome = await run_install(
        Path(args.ipa), udid=args.udid, team_id=args.team,
        strip_extensions=False if args.keep_extensions else None,
        revoke_conflicting_cert=args.revoke_conflicting_cert,
        progress=progress,
    )
    print(f"\r  Installiert ueber {outcome.transport}.")
    print(f"\n{outcome.name} laeuft jetzt als {outcome.bundle_id}")
    print(f"Gueltig fuer {outcome.days_valid:.1f} Tage.")
    if outcome.days_valid < 10:
        print("Vor Ablauf erneuern mit: modstaller refresh")
    return 0


async def _refresh(args) -> int:
    from .pipeline import refresh as run_refresh

    results = await run_refresh(
        udid=args.udid, only=args.bundle_id,
        threshold_days=args.threshold, progress=_progress_printer(),
    )
    if results:
        print(f"\r  {len(results)} App(s) erneuert.")
    return 0


async def _uninstall(args) -> int:
    from .device.connection import ServiceProvider
    from .device.install import uninstall_app
    from .state import store

    async with ServiceProvider(args.udid) as sp:
        transport = await uninstall_app(sp, args.bundle_id)
    print(f"{args.bundle_id} entfernt (Transport: {transport}).")
    if store.forget(args.bundle_id):
        print("Aus der Refresh-Liste ausgetragen.")
    return 0


async def _list(args) -> int:
    from .state import store
    rows = store.all_installs()
    if not rows:
        print("Noch nichts ueber ModStaller installiert.")
        return 0
    for r in rows:
        mark = "!" if r.days_left < 2 else " "
        print(f" {mark} {r.name:<26} {r.expiry_text}")
        print(f"   {r.bundle_id}")
    return 0


# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="modstaller",
        description="iOS-Sideloader fuer Linux: IPAs signieren und installieren.")
    p.add_argument("-u", "--udid", help="Zielgeraet (Default: das einzige)")
    p.add_argument("--debug", action="store_true",
                   help="vollen Stacktrace bei unerwarteten Fehlern zeigen")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Pruefen, ob alles Noetige da ist"
                   ).set_defaults(func=cmd_doctor)

    log = sub.add_parser("login", help="Bei Apple anmelden")
    log.add_argument("apple_id", nargs="?", help="Apple ID (sonst Nachfrage)")
    log.set_defaults(afunc=_login)

    out = sub.add_parser("logout", help="Anmeldung verwerfen")
    out.add_argument("--forget-device", action="store_true",
                     help="auch die Geraete-Identitaet verwerfen (erzwingt 2FA)")
    out.set_defaults(func=_logout)

    sub.add_parser("account", help="Team, Kontingente, Geraete"
                   ).set_defaults(afunc=_account)

    dev = sub.add_parser("device", help="Geraete-Infos")
    devsub = dev.add_subparsers(dest="subcmd", required=True)
    devsub.add_parser("info", help="Modell, iOS-Version, Developer Mode"
                      ).set_defaults(afunc=_device_info)
    devsub.add_parser("apps", help="Installierte Nutzer-Apps"
                      ).set_defaults(afunc=_device_apps)

    ins = sub.add_parser("install", help="IPA signieren und installieren")
    ins.add_argument("ipa", help="Pfad zur IPA")
    ins.add_argument("--team", help="Team-ID, falls mehrere vorhanden")
    ins.add_argument("--no-sign", action="store_true",
                     help="IPA ist bereits signiert, nur installieren")
    ins.add_argument("--keep-extensions", action="store_true",
                     help="App-Extensions behalten (kostet je eine App-ID)")
    ins.add_argument("--revoke-conflicting-cert", action="store_true",
                     help="fremde Development-Zertifikate widerrufen, falls "
                          "Apples Limit ein eigenes verhindert (Apps, die "
                          "damit signiert wurden, starten danach nicht mehr)")
    ins.set_defaults(afunc=_install)

    ref = sub.add_parser("refresh",
                         help="Ablaufende Apps neu signieren und installieren")
    ref.add_argument("bundle_id", nargs="?",
                     help="nur diese App (Default: alle faelligen)")
    ref.add_argument("--threshold", type=float,
                     help="Tage vor Ablauf, ab denen erneuert wird")
    ref.set_defaults(afunc=_refresh)

    uni = sub.add_parser("uninstall", help="App vom iPhone entfernen")
    uni.add_argument("bundle_id", help="Bundle-ID der App")
    uni.set_defaults(afunc=_uninstall)

    crt = sub.add_parser("certs", help="Development-Zertifikate anzeigen")
    crt.add_argument("--team", help="Team-ID, falls mehrere vorhanden")
    crt.add_argument("--revoke", metavar="ID",
                     help="Zertifikat widerrufen, um Platz zu schaffen")
    crt.add_argument("--yes", action="store_true",
                     help="Rueckfrage beim Widerrufen ueberspringen")
    crt.set_defaults(afunc=_certs)

    sub.add_parser("list", help="Installierte Apps und Ablaufdaten"
                   ).set_defaults(afunc=_list)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args_debug = getattr(args, "debug", False)
    config.ensure_dirs()
    try:
        if hasattr(args, "afunc"):
            return asyncio.run(args.afunc(args))
        return args.func(args)
    except ModStallerError as exc:
        print(f"\nFehler: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130
    except Exception as exc:
        # Netz- und Bibliotheksfehler sollen nicht als Traceback erscheinen.
        # Der volle Stack bleibt ueber --debug erreichbar.
        import requests
        if isinstance(exc, requests.exceptions.RetryError):
            print("\nFehler: Apple hat wiederholt abgewiesen und der Versuch "
                  "wurde aufgegeben.\nMeist Drosselung - 15-60 Minuten warten.",
                  file=sys.stderr)
        elif isinstance(exc, requests.exceptions.SSLError):
            print(f"\nFehler: TLS-Verbindung zu Apple fehlgeschlagen.\n{exc}",
                  file=sys.stderr)
        elif isinstance(exc, requests.exceptions.RequestException):
            print(f"\nFehler: Netzwerkproblem im Kontakt mit Apple.\n{exc}",
                  file=sys.stderr)
        else:
            if args_debug:
                raise
            print(f"\nUnerwarteter Fehler: {type(exc).__name__}: {exc}\n"
                  "Vollen Stack mit --debug anzeigen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
