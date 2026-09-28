"""Command line. Deliberately contains no logic - only arguments and output."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from . import config
from .errors import ModStallerError, describe


def _windows_console() -> None:
    """UTF-8 and ANSI colors in the classic Windows console, too.

    Without this, even the check mark in the system check dies with a
    UnicodeEncodeError (cp1252), and the color codes show up raw.
    """
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for std in (-11, -12):          # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
            handle = kernel32.GetStdHandle(std)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass  # no console (redirected) - then colors aren't needed either


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


async def _doctor(args) -> int:
    from .doctor import problems, run_checks, todos

    print("ModStaller - system check\n")
    checks = await run_checks()
    for c in checks:
        detail = c.detail
        if not c.ok and c.kind == "problem" and c.hint:
            detail = f"{detail} - {c.hint}" if detail else c.hint
        (_ok if c.ok else _fail)(c.label, detail)

    print()
    bad, todo = problems(checks), todos(checks)
    if bad:
        print(f"{len(bad)} item(s) to resolve, see above.")
    elif todo:
        print("System is ready. Still to do:")
        for c in todo:
            print(f"  - {c.hint}")
    else:
        print("All set.")
    return 1 if bad else 0


# -- Sign-in ---------------------------------------------------------------


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
        print("No Apple ID given.", file=sys.stderr)
        return 2
    password = getpass.getpass("Password (not stored): ")

    print("\nPreparing anisette …", flush=True)
    ani = _anisette()

    def prompt_code() -> str:
        return input("2FA code from your iPhone: ").strip()

    print("Signing in to Apple …", flush=True)
    session = login(apple_id, password, ani, code_prompt=prompt_code,
                    debug=args.debug)
    print("\nSigned in.")

    print("\nTeams:")
    for t in DeveloperServices(session, ani).list_teams():
        print(f"  {t}")
    return 0


def _logout(args) -> int:
    from .apple.session import Session
    Session.clear()
    print("Signed out.")
    if args.forget_device:
        from .apple.anisette import DEVICE_FILE, PROVISIONING_FILE
        for f in (PROVISIONING_FILE, DEVICE_FILE):
            f.unlink(missing_ok=True)
        print("Device identity discarded - on the next login Apple will "
              "ask for a 2FA code again.")
    return 0


async def _account(args) -> int:
    from .apple.devservices import DeveloperServices
    from .apple.session import Session
    from .provisioning import Capabilities

    session = Session.load()
    if session is None:
        print("Not signed in. First run: modstaller login", file=sys.stderr)
        return 3

    ani = _anisette()
    api = DeveloperServices(session, ani)
    for t in api.list_teams():
        caps = Capabilities.for_team(t)
        print(t)
        print(f"  {caps.describe()}")
        print(f"  Devices: {len(api.list_devices(t.team_id))}")
        app_ids = api.list_app_ids(t.team_id)
        if caps.max_app_ids_per_week:
            left = caps.max_app_ids_per_week - len(app_ids)
            note = (f" - {left} left" if left > 0
                    else " - quota used up, ModStaller will recycle an old "
                         "one on the next install")
            print(f"  App IDs: {len(app_ids)}/{caps.max_app_ids_per_week}{note}")
        else:
            print(f"  App IDs: {len(app_ids)}")
        for a in app_ids:
            print(f"    {a.identifier}")
    return 0


async def _certs(args) -> int:
    from .apple.devservices import DeveloperServices
    from .apple.session import Session
    from .provisioning import pick_team

    session = Session.load()
    if session is None:
        print("Not signed in. First run: modstaller login", file=sys.stderr)
        return 3
    ani = _anisette()
    api = DeveloperServices(session, ani)
    team = pick_team(api.list_teams(), args.team)
    certs = api.list_certificates(team.team_id)

    if args.revoke:
        match = [c for c in certs
                 if args.revoke in (c.cert_id, c.serial, c.name)]
        if not match:
            print(f"No certificate matching {args.revoke!r} found.",
                  file=sys.stderr)
            return 2
        cert = match[0]
        print(f"Revoking: {cert}")
        print("Apps signed with it will no longer launch afterwards.")
        if not args.yes:
            if input("Really revoke? [yes/NO] ").strip().lower() not in (
                    "ja", "j", "yes", "y"):
                print("Cancelled.")
                return 0
        api.revoke_certificate(team.team_id, cert.serial)
        print("Revoked.")
        return 0

    if not certs:
        print("No development certificates in the account.")
        return 0
    print(f"{len(certs)} development certificate(s):\n")
    for c in certs:
        print(f"  {c}")
    print("\nModStaller cannot reuse any of them - the private key\n"
          "lives with the tool that requested it.")
    return 0


# -- Device ----------------------------------------------------------------


async def _device_info(args) -> int:
    from .device.connection import ServiceProvider, device_info
    async with ServiceProvider(args.udid) as sp:
        info = await device_info(sp.lockdown)
        print(info)
        if not info.developer_mode:
            print("\n  Developer Mode is off. Turn it on on the iPhone under\n"
                  "  Settings > Privacy & Security > Developer Mode,\n"
                  "  otherwise no sideloaded app will launch.")
    return 0


async def _device_apps(args) -> int:
    from .device.connection import ServiceProvider
    from .device.install import list_apps
    async with ServiceProvider(args.udid) as sp:
        apps = await list_apps(sp)
        if not apps:
            print("No user apps found.")
            return 0
        for bid, meta in sorted(apps.items()):
            print(f"  {meta.get('CFBundleDisplayName', bid):<34} {bid}")
        print(f"\n{len(apps)} App(s).")
    return 0


# -- Install --------------------------------------------------------------


async def _install(args) -> int:
    from .pipeline import install as run_install

    progress = _progress_printer()

    if args.no_sign:
        from .device.connection import ServiceProvider
        from .device.install import install_ipa
        async with ServiceProvider(args.udid) as sp:
            res = await install_ipa(sp, Path(args.ipa), progress=progress)
            print(f"\r  Installed (transport: {res.transport})")
        return 0

    outcome = await run_install(
        Path(args.ipa), udid=args.udid, team_id=args.team,
        strip_extensions=False if args.keep_extensions else None,
        revoke_conflicting_cert=args.revoke_conflicting_cert,
        progress=progress,
    )
    print(f"\r  Installed via {outcome.transport}.")
    print(f"\n{outcome.name} now runs as {outcome.bundle_id}")
    print(f"Valid for {outcome.days_valid:.1f} days.")
    if outcome.days_valid < 10:
        print("Renew before it expires with: modstaller refresh")
    return 0


async def _refresh(args) -> int:
    from .pipeline import refresh as run_refresh

    results = await run_refresh(
        udid=args.udid, only=args.bundle_id,
        threshold_days=args.threshold, progress=_progress_printer(),
    )
    if results:
        print(f"\r  {len(results)} app(s) renewed.")
    return 0


async def _jit(args) -> int:
    from .device.connection import ServiceProvider
    from .device.jit import enable_jit
    from .state import store

    bundle_id = args.bundle_id
    if bundle_id is None:
        apps = store.all_installs()
        if len(apps) != 1:
            print("Please give the bundle ID (modstaller list shows it).",
                  file=sys.stderr)
            return 2
        bundle_id = apps[0].bundle_id

    async with ServiceProvider(args.udid) as sp:
        result = await enable_jit(sp, bundle_id,
                                 on_step=lambda m: print(f"  {m}", flush=True),
                                 verbose=args.debug)

    print()
    print(result.summary)
    for note in result.notes:
        print(f"  Note: {note}")

    if result.txm and not result.prepared_regions:
        print("\nThe app did not request any memory while we waited.\n"
              "Possible reasons:\n"
              "  - No instance was started in the app. The need only "
              "arises then.\n"
              "  - The app does not ask via the breakpoint mechanism that "
              "iOS 26+ requires.\n"
              "JIT only applies to this launch of the app anyway.")
        return 1

    print("\nJIT only applies to this launch - after the app quits it\n"
          "has to be enabled again.")
    return 0


async def _uninstall(args) -> int:
    from .device.connection import ServiceProvider
    from .device.install import uninstall_app
    from .state import store

    async with ServiceProvider(args.udid) as sp:
        transport = await uninstall_app(sp, args.bundle_id)
    print(f"{args.bundle_id} removed (transport: {transport}).")
    if store.forget(args.bundle_id):
        print("Removed from the refresh list.")
    return 0


async def _list(args) -> int:
    from .state import store
    rows = store.all_installs()
    if not rows:
        print("Nothing installed via ModStaller yet.")
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
        description="iOS sideloader for Linux: sign and install IPAs.")
    p.add_argument("-u", "--udid", help="target device (default: the only one)")
    p.add_argument("--debug", action="store_true",
                   help="show the full stack trace on unexpected errors")
    # The graphical interface is a separate client (gui/) that talks to us
    # via "serve". The subcommands remain for scripts and the refresh
    # service.
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("doctor", help="Check that everything needed is there"
                   ).set_defaults(afunc=_doctor)

    log = sub.add_parser("login", help="Sign in to Apple")
    log.add_argument("apple_id", nargs="?", help="Apple ID (prompted otherwise)")
    log.set_defaults(afunc=_login)

    out = sub.add_parser("logout", help="Discard the sign-in")
    out.add_argument("--forget-device", action="store_true",
                     help="also discard the device identity (forces 2FA)")
    out.set_defaults(func=_logout)

    sub.add_parser("account", help="Team, quotas, devices"
                   ).set_defaults(afunc=_account)

    dev = sub.add_parser("device", help="Device info")
    devsub = dev.add_subparsers(dest="subcmd", required=True)
    devsub.add_parser("info", help="Model, iOS version, Developer Mode"
                      ).set_defaults(afunc=_device_info)
    devsub.add_parser("apps", help="Installed user apps"
                      ).set_defaults(afunc=_device_apps)

    ins = sub.add_parser("install", help="Sign and install an IPA")
    ins.add_argument("ipa", help="path to the IPA")
    ins.add_argument("--team", help="team ID, if there are several")
    ins.add_argument("--no-sign", action="store_true",
                     help="IPA is already signed, only install it")
    ins.add_argument("--keep-extensions", action="store_true",
                     help="keep app extensions (costs one App ID each)")
    ins.add_argument("--revoke-conflicting-cert", action="store_true",
                     help="revoke other development certificates if "
                          "Apple's limit prevents creating our own (apps "
                          "signed with them will no longer launch)")
    ins.set_defaults(afunc=_install)

    ref = sub.add_parser("refresh",
                         help="Re-sign and reinstall expiring apps")
    ref.add_argument("bundle_id", nargs="?",
                     help="only this app (default: all due)")
    ref.add_argument("--threshold", type=float,
                     help="days before expiry from which to renew")
    ref.set_defaults(afunc=_refresh)

    jit = sub.add_parser("jit", help="Enable JIT for an app "
                                     "(needed for Java and emulator apps)")
    jit.add_argument("bundle_id", nargs="?",
                     help="bundle ID (default: the only one installed)")
    jit.set_defaults(afunc=_jit)

    uni = sub.add_parser("uninstall", help="Remove an app from the iPhone")
    uni.add_argument("bundle_id", help="bundle ID of the app")
    uni.set_defaults(afunc=_uninstall)

    crt = sub.add_parser("certs", help="Show development certificates")
    crt.add_argument("--team", help="team ID, if there are several")
    crt.add_argument("--revoke", metavar="ID",
                     help="revoke a certificate to make room")
    crt.add_argument("--yes", action="store_true",
                     help="skip the confirmation when revoking")
    crt.set_defaults(afunc=_certs)

    sub.add_parser("list", help="Installed apps and expiry dates"
                   ).set_defaults(afunc=_list)

    # For the interface, not for humans - hence no help.
    sub.add_parser("serve", help=argparse.SUPPRESS).set_defaults(func=_serve)
    return p


def _serve(args) -> int:
    from .server import main as serve_main
    return serve_main()


def main(argv: list[str] | None = None) -> int:
    _windows_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    args_debug = getattr(args, "debug", False)
    config.ensure_dirs()

    if args.cmd is None:
        parser.print_help()
        return 0
    if args.cmd != "serve":
        # "serve" sets up its own log - with the live view for the interface.
        from . import logbook
        logbook.setup(file=config.LOG_FILE, book=None, echo=True)

    try:
        if hasattr(args, "afunc"):
            return asyncio.run(args.afunc(args))
        return args.func(args)
    except ModStallerError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        # The full stack stays available via --debug.
        text = describe(exc)
        if text is not None:
            print(f"\nError: {text}", file=sys.stderr)
        elif args_debug:
            raise
        else:
            print(f"\nUnexpected error: {type(exc).__name__}: {exc}\n"
                  "Show the full stack with --debug.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
