"""Interaktive Oberflaeche.

Leitgedanke: erst zeigen, dann fragen. Der Kopf beantwortet die drei Fragen,
die vor jeder Aktion zaehlen - haengt das iPhone dran, sind wir angemeldet,
laeuft gleich etwas ab - und das Menue bietet vorrangig an, was gerade
dran ist. Wer nur eine App installieren will, soll nicht erst lernen, in
welcher Reihenfolge Apple Zertifikate, App-IDs und Profile verlangt.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import questionary
from questionary import Choice, Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import config
from .errors import ModStallerError

console = Console()

#: Zurueckhaltend gehalten - die Farbe soll Zustand zeigen, nicht dekorieren.
STYLE = Style([
    ("qmark", "fg:#5f87ff bold"),
    ("question", "bold"),
    ("pointer", "fg:#5f87ff bold"),
    ("highlighted", "fg:#5f87ff bold"),
    ("selected", "fg:#87d787"),
    ("answer", "fg:#87d787"),
    ("disabled", "fg:#6c6c6c italic"),
])

OK, WARN, BAD, DIM = "green", "yellow", "red", "dim"

#: Ab hier gilt ein Profil als dringend.
URGENT_DAYS = 2.0

#: Wo wir nach IPAs suchen, wenn keine angegeben wird.
IPA_DIRS = (Path.home() / "Downloads", Path.home() / "Dokumente",
            Path.home() / "Desktop", Path.home() / "Schreibtisch")


# -- Zustand ---------------------------------------------------------------


@dataclass
class Status:
    device_name: str | None = None
    ios_version: str = ""
    developer_mode: bool = True
    logged_in: bool = False
    apps: list = None
    error: str = ""

    @property
    def has_device(self) -> bool:
        return self.device_name is not None

    @property
    def urgent(self) -> list:
        return [a for a in (self.apps or []) if a.days_left <= URGENT_DAYS]


async def gather_status() -> Status:
    """Nur lokal und ueber USB - keine Apple-Abfrage.

    Der Kopf soll sofort stehen. Kontingente kosten einen Netzaufruf und
    werden deshalb erst im Konto-Menue geholt.
    """
    from .apple.session import Session
    from .state import store

    st = Status(apps=store.all_installs(), logged_in=Session.load() is not None)
    try:
        from .device.connection import ServiceProvider, device_info
        async with ServiceProvider() as sp:
            info = await device_info(sp.lockdown)
            st.device_name = info.name
            st.ios_version = info.ios_version
            st.developer_mode = info.developer_mode
    except ModStallerError:
        pass  # kein Geraet - das ist ein Zustand, kein Fehler
    except Exception as exc:
        st.error = str(exc)
    return st


# -- Darstellung -----------------------------------------------------------


def _dot(colour: str) -> Text:
    return Text("● ", style=colour)


def render_header(st: Status) -> None:
    body = Text()

    if st.has_device:
        body.append_text(_dot(OK if st.developer_mode else WARN))
        body.append(f"{st.device_name} · iOS {st.ios_version}")
        if not st.developer_mode:
            body.append("  (Entwicklermodus aus)", style=WARN)
    else:
        body.append_text(_dot(DIM))
        body.append("Kein iPhone verbunden", style=DIM)
    body.append("\n")

    body.append_text(_dot(OK if st.logged_in else WARN))
    body.append("Bei Apple angemeldet" if st.logged_in
                else "Nicht angemeldet", style="" if st.logged_in else WARN)

    console.print(Panel(body, title="ModStaller", title_align="left",
                        border_style="#5f87ff", padding=(0, 1)))

    if not st.apps:
        return

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(width=2)
    table.add_column(style="bold")
    table.add_column()
    for app in st.apps:
        days = app.days_left
        colour = BAD if days < 0 else (WARN if days <= URGENT_DAYS else OK)
        table.add_row(Text("●", style=colour), app.name,
                      Text(app.expiry_text, style=colour))
    console.print(table)
    console.print()


# -- Hilfen ----------------------------------------------------------------


async def _ask(question) -> object:
    return await question.ask_async()


async def select(message: str, choices: list, **kw) -> object:
    return await _ask(questionary.select(message, choices=choices,
                                         style=STYLE, **kw))


async def confirm(message: str, default: bool = False) -> bool:
    return bool(await _ask(questionary.confirm(message, default=default,
                                               style=STYLE)))


def fail(exc: Exception) -> None:
    console.print()
    console.print(Panel(Text(str(exc)), title="Fehlgeschlagen",
                        title_align="left", border_style=BAD, padding=(0, 1)))


def done(message: str) -> None:
    console.print(Text(f"✓ {message}", style=OK))


async def pause() -> None:
    await _ask(questionary.press_any_key_to_continue(
        "Weiter mit einer beliebigen Taste …", style=STYLE))


def find_ipas() -> list[Path]:
    seen: list[Path] = []
    for d in IPA_DIRS:
        if d.is_dir():
            seen.extend(sorted(d.glob("*.ipa")))
    return seen


# -- Aktionen --------------------------------------------------------------


async def action_install(st: Status) -> None:
    from .pipeline import install as run_install

    found = find_ipas()
    choices = [
        Choice(f"{p.name}  ({p.stat().st_size / 1e6:.0f} MB)", value=p)
        for p in found
    ]
    choices.append(Choice("Anderer Pfad …", value="other"))
    choices.append(Choice("Zurueck", value=None))

    picked = await select("Welche IPA?", choices)
    if picked is None:
        return
    if picked == "other":
        answer = await _ask(questionary.path(
            "Pfad zur IPA:", validate=lambda p: (
                True if Path(p).expanduser().is_file()
                else "Datei nicht gefunden"), style=STYLE))
        if not answer:
            return
        picked = Path(answer).expanduser()

    if not st.has_device:
        console.print(Text("Kein iPhone verbunden - bitte anstecken und "
                           "entsperren.", style=WARN))
        await pause()
        return

    keep_ext = False
    from .signing.ipa import inspect
    try:
        info = inspect(picked)
    except ModStallerError as exc:
        fail(exc)
        await pause()
        return

    if info.extensions:
        keep_ext = await confirm(
            f"{len(info.extensions)} App-Extension(s) behalten? "
            f"(kostet je eine App-ID vom Wochenkontingent)", default=False)

    console.print()
    try:
        outcome = await run_install(
            picked, strip_extensions=False if keep_ext else None,
            progress=_progress_bar())
        console.print()
        done(f"{outcome.name} installiert - laeuft {outcome.days_valid:.0f} Tage")
    except ModStallerError as exc:
        fail(exc)
    await pause()


def _progress_bar():
    last = [-1]

    def progress(pct: int) -> None:
        if pct == last[0]:
            return
        last[0] = pct
        filled = pct * 30 // 100
        bar = "━" * filled + "─" * (30 - filled)
        console.print(f"  [green]{bar}[/green] {pct:3d}%", end="\r")

    return progress


async def action_manage(st: Status) -> None:
    from .state import store

    while True:
        apps = store.all_installs()
        if not apps:
            console.print(Text("Noch nichts ueber ModStaller installiert.",
                               style=DIM))
            await pause()
            return

        choices = []
        for a in apps:
            days = a.days_left
            mark = "!" if days <= URGENT_DAYS else " "
            choices.append(Choice(f"{mark} {a.name:<24} {a.expiry_text}",
                                  value=a))
        choices.append(Choice("Alle faelligen erneuern", value="refresh-all"))
        choices.append(Choice("Zurueck", value=None))

        picked = await select("Welche App?", choices)
        if picked is None:
            return
        if picked == "refresh-all":
            await _refresh(None)
            continue
        await _app_menu(picked)


async def _app_menu(app) -> None:
    what = await select(f"{app.name} · {app.expiry_text}", [
        Choice("Starten und JIT freischalten (fuer Java- und Emulator-Apps)",
               value="jit"),
        Choice("Jetzt erneuern (neu signieren und installieren)",
               value="refresh"),
        Choice("Vom iPhone entfernen", value="uninstall"),
        Choice("Zurueck", value=None),
    ])
    if what == "jit":
        await _enable_jit(app)
    elif what == "refresh":
        await _refresh(app.bundle_id)
    elif what == "uninstall":
        if not await confirm(f"{app.name} wirklich vom iPhone entfernen?"):
            return
        from .device.connection import ServiceProvider
        from .device.install import uninstall_app
        from .state import store
        try:
            async with ServiceProvider() as sp:
                await uninstall_app(sp, app.bundle_id)
            store.forget(app.bundle_id)
            done(f"{app.name} entfernt")
        except ModStallerError as exc:
            fail(exc)
        await pause()


async def _enable_jit(app) -> None:
    from .device.connection import ServiceProvider
    from .device.jit import enable_jit

    console.print()
    try:
        async with ServiceProvider() as sp:
            result = await enable_jit(sp, app.bundle_id,
                                      on_step=lambda m: console.print(
                                          Text(f"  {m}", style=DIM)))
        console.print()
        if result.prepared_regions:
            done(f"{app.name}: {result.summary}")
            console.print(Text(
                "Gilt nur fuer diesen Start - nach dem Beenden der App "
                "erneut freischalten.", style=DIM))
        else:
            console.print(Text(result.summary, style=WARN))
            console.print(Text(
                "Im Programm muss waehrend des Wartens eine Instanz "
                "gestartet werden - erst dann fragt es nach Speicher.",
                style=DIM))
        for note in result.notes:
            console.print(Text(f"  {note}", style=DIM))
    except ModStallerError as exc:
        fail(exc)
    await pause()


async def _refresh(bundle_id: str | None) -> None:
    from .pipeline import refresh as run_refresh
    console.print()
    try:
        results = await run_refresh(only=bundle_id, progress=_progress_bar())
        console.print()
        done(f"{len(results)} App(s) erneuert" if results
             else "Nichts war faellig")
    except ModStallerError as exc:
        fail(exc)
    await pause()


async def action_account(st: Status) -> None:
    from .apple.session import Session

    while True:
        session = Session.load()
        choices = []
        if session is None:
            choices.append(Choice("Bei Apple anmelden", value="login"))
        else:
            choices.append(Choice("Konto und Kontingente anzeigen",
                                  value="info"))
            choices.append(Choice("Zertifikate verwalten", value="certs"))
            choices.append(Choice("Abmelden", value="logout"))
        choices.append(Choice("Zurueck", value=None))

        what = await select("Konto", choices)
        if what is None:
            return
        if what == "login":
            await _login()
        elif what == "info":
            await _account_info()
        elif what == "certs":
            await _certs_menu()
        elif what == "logout":
            forget = await confirm(
                "Auch die Geraete-Identitaet verwerfen? "
                "(dann fragt Apple beim naechsten Mal wieder einen 2FA-Code ab)",
                default=False)
            Session.clear()
            if forget:
                from .apple.anisette import DEVICE_FILE, PROVISIONING_FILE
                for f in (PROVISIONING_FILE, DEVICE_FILE):
                    f.unlink(missing_ok=True)
            done("Abgemeldet")
            await pause()


async def _login() -> None:
    from .apple import anisette as anisette_mod
    from .apple.session import login

    apple_id = await _ask(questionary.text("Apple ID:", style=STYLE))
    if not apple_id:
        return
    password = await _ask(questionary.password(
        "Passwort (wird nicht gespeichert):", style=STYLE))
    if not password:
        return

    settings = config.Settings.load()
    console.print(Text("Anisette vorbereiten …", style=DIM))
    ani = anisette_mod.build(settings.anisette_provider,
                            settings.anisette_server)

    def prompt_code() -> str:
        return questionary.text(
            "2FA-Code von deinem iPhone:", style=STYLE).ask() or ""

    console.print(Text("Bei Apple anmelden …", style=DIM))
    try:
        login(apple_id, password, ani, code_prompt=prompt_code)
        done("Angemeldet")
    except ModStallerError as exc:
        fail(exc)
    await pause()


async def _with_api():
    from .apple import anisette as anisette_mod
    from .apple.devservices import DeveloperServices
    from .apple.session import Session
    settings = config.Settings.load()
    ani = anisette_mod.build(settings.anisette_provider,
                            settings.anisette_server)
    return DeveloperServices(Session.load(), ani)


async def _account_info() -> None:
    from .provisioning import Capabilities
    console.print(Text("Bei Apple nachfragen …", style=DIM))
    try:
        api = await _with_api()
        for team in api.list_teams():
            caps = Capabilities.for_team(team)
            app_ids = api.list_app_ids(team.team_id)
            devices = api.list_devices(team.team_id)

            t = Table(show_header=False, box=None, padding=(0, 1))
            t.add_column(style="bold")
            t.add_column()
            t.add_row("Team", f"{team.name} [{team.team_id}]")
            t.add_row("Art", caps.describe())
            t.add_row("Geraete", str(len(devices)))
            if caps.max_app_ids_per_week:
                left = caps.max_app_ids_per_week - len(app_ids)
                style = WARN if left <= 1 else ""
                t.add_row("App-IDs", Text(
                    f"{len(app_ids)}/{caps.max_app_ids_per_week}"
                    + (f" - noch {left} frei" if left > 0
                       else " - ausgeschoepft, alte werden recycelt"),
                    style=style))
            else:
                t.add_row("App-IDs", str(len(app_ids)))
            console.print(t)
    except ModStallerError as exc:
        fail(exc)
    await pause()


async def _certs_menu() -> None:
    from .provisioning import pick_team
    console.print(Text("Bei Apple nachfragen …", style=DIM))
    try:
        api = await _with_api()
        team = pick_team(api.list_teams())
        certs = api.list_certificates(team.team_id)
    except ModStallerError as exc:
        fail(exc)
        await pause()
        return

    if not certs:
        console.print(Text("Keine Development-Zertifikate im Account.",
                           style=DIM))
        await pause()
        return

    choices = [Choice(str(c), value=c) for c in certs]
    choices.append(Choice("Zurueck", value=None))
    picked = await select(
        "Zertifikate (Apple erlaubt nur wenige gleichzeitig)", choices)
    if picked is None:
        return

    console.print(Text(
        "Ein Widerruf macht alle Apps unbrauchbar, die mit diesem Zertifikat "
        "signiert wurden - sie starten danach nicht mehr.", style=WARN))
    if not await confirm(f"{picked.name} wirklich widerrufen?"):
        return
    try:
        api.revoke_certificate(team.team_id, picked.serial)
        done("Widerrufen")
    except ModStallerError as exc:
        fail(exc)
    await pause()


async def action_device(st: Status) -> None:
    from .device.connection import ServiceProvider, device_info
    from .device.install import list_apps
    try:
        async with ServiceProvider() as sp:
            info = await device_info(sp.lockdown)
            t = Table(show_header=False, box=None, padding=(0, 1))
            t.add_column(style="bold")
            t.add_column()
            t.add_row("Name", info.name)
            t.add_row("Modell", info.product_type)
            t.add_row("iOS", f"{info.ios_version} ({info.build})")
            t.add_row("UDID", info.udid)
            t.add_row("Entwicklermodus",
                      Text("an", style=OK) if info.developer_mode
                      else Text("aus - sideloadete Apps starten nicht",
                                style=BAD))
            console.print(t)

            if await confirm("Installierte Apps auflisten?", default=False):
                apps = await list_apps(sp)
                console.print(Text(f"\n{len(apps)} Nutzer-App(s):", style=DIM))
                for bid, meta in sorted(apps.items()):
                    console.print(
                        f"  {meta.get('CFBundleDisplayName', bid):<30} "
                        f"[dim]{bid}[/dim]")
    except ModStallerError as exc:
        fail(exc)
    await pause()


async def action_doctor(st: Status) -> None:
    from .cli import cmd_doctor
    console.print()
    cmd_doctor(None)
    await pause()


# -- Hauptschleife ---------------------------------------------------------


def build_menu(st: Status) -> list:
    """Stellt das Menue nach Lage zusammen.

    Was gerade ansteht, kommt nach oben: ohne Anmeldung nuetzt kein anderer
    Punkt etwas, und ein Profil, das in Stunden ablaeuft, ist dringender als
    alles andere. Der Rest bleibt in fester Reihenfolge, damit sich die
    Bedienung einpraegt.
    """
    choices = []
    if not st.logged_in:
        choices.append(Choice("Bei Apple anmelden", value=action_account))
    if st.urgent:
        first = st.urgent[0]
        choices.append(Choice(f"{first.name} laeuft ab - jetzt erneuern",
                              value="urgent"))
    return choices + [
        Choice("App installieren", value=action_install),
        Choice("Installierte Apps verwalten", value=action_manage),
        Choice("Konto und Zertifikate", value=action_account),
        Choice("Geraet", value=action_device),
        Choice("Systemcheck", value=action_doctor),
        Choice("Beenden", value=None),
    ]


async def run() -> int:
    config.ensure_dirs()
    console.print()
    while True:
        st = await gather_status()
        render_header(st)
        if st.error:
            console.print(Text(f"Hinweis: {st.error}", style=WARN))

        picked = await select("Was moechtest du tun?", build_menu(st))
        console.clear()
        if picked is None:
            return 0
        if picked == "urgent":
            await _refresh(None)
            continue
        try:
            await picked(st)
        except KeyboardInterrupt:
            console.print(Text("\nAbgebrochen.", style=DIM))
        console.clear()


def main() -> int:
    try:
        return asyncio.run(run())
    except (KeyboardInterrupt, EOFError):
        console.print()
        return 130
