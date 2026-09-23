"""Ist das iPhone bereit fuers Sideloading - und was davon kann ModStaller selbst erledigen?

Jede Pruefung sagt, was los ist, und - wo es geht - wie man es behebt:
entweder automatisch (``fix``) oder mit einer Anleitung (``manual``), wenn
Apple den Schritt dem Menschen am Geraet vorbehaelt.

Zwei Grenzen setzt iOS selbst:

* **Entwicklermodus mit Code-Sperre.** Ohne Code schaltet AMFI ihn auf
  Zuruf ein, startet neu und laesst sich die Nachfrage bestaetigen. Mit Code
  verweigert es das. Dann machen wir wenigstens den Schalter in den
  Einstellungen sichtbar - bis ein Entwicklerwerkzeug das tut, fehlt er dort.
* **"Entwickler vertrauen".** Dafuer gibt es keine Schnittstelle; das bleibt
  ein Fingertipp in den Einstellungen.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from ..errors import DeviceError, DeviceNotFound, NotPaired
from .connection import ServiceProvider, device_info

OK, WARN, BAD, INFO, NA = "ok", "warn", "bad", "info", "na"

FIX_PAIR = "pair"
FIX_DEVELOPER_MODE = "developer-mode"
FIX_DDI = "ddi"
FIX_EXPIRED_PROFILES = "expired-profiles"

#: Gratis-Accounts: so viele sideloadete Apps laesst iOS gleichzeitig zu.
FREE_APP_LIMIT = 3

#: Darunter wird es fuer groessere IPAs knapp.
LOW_SPACE_BYTES = 1_000_000_000

#: Pairing-Dialog und Neustart brauchen einen Menschen - also Geduld.
PAIR_TIMEOUT = 90.0
DEVELOPER_MODE_TIMEOUT = 300.0

TRUST_HINT = (
    "Beim ersten Start einer App: Einstellungen › Allgemein › VPN & "
    "Geräteverwaltung › deine Apple-ID › „Vertrauen“. Pro Zertifikat einmal."
)
DEVELOPER_MODE_HINT = (
    "Einstellungen › Datenschutz & Sicherheit › Entwicklermodus einschalten. "
    "Das iPhone startet neu; danach „Einschalten“ bestätigen und den Code "
    "eingeben."
)


@dataclass
class Check:
    id: str
    label: str
    state: str
    detail: str = ""
    #: Kennung fuer :func:`run_fix`, wenn ModStaller es selbst beheben kann.
    fix: str | None = None
    fix_label: str = ""
    #: Was der Mensch am iPhone tun muss, wenn es keine Automatik gibt.
    manual: str = ""


@dataclass
class FixResult:
    message: str
    #: Leer, wenn alles erledigt ist - sonst der verbleibende Handgriff.
    manual: str = ""


def _major(version: str) -> int:
    try:
        return int(version.split(".")[0])
    except ValueError:
        return 0


def _gb(n: int) -> str:
    return f"{n / 1e9:.1f} GB"


# -- Pruefen -----------------------------------------------------------------


async def run_checks(udid: str | None = None) -> list[Check]:
    """Alle Pruefungen. Ohne angestecktes iPhone eine leere Liste."""
    try:
        async with ServiceProvider(udid) as sp:
            return await _checks(sp)
    except DeviceNotFound:
        return []
    except NotPaired as exc:
        from pymobiledevice3.exceptions import PasswordRequiredError
        if isinstance(exc.__cause__, PasswordRequiredError):
            return [Check("pairing", "iPhone entsperrt", BAD,
                          "Das iPhone ist gesperrt.",
                          manual="iPhone entsperren - die Prüfung läuft dann "
                                 "von selbst weiter.")]
        return [Check("pairing", "Mit diesem Rechner gekoppelt", BAD,
                      "Das iPhone vertraut diesem Rechner noch nicht.",
                      fix=FIX_PAIR, fix_label="Kopplung anfragen",
                      manual="Am iPhone „Vertrauen“ tippen und den Code "
                             "eingeben.")]


async def _checks(sp: ServiceProvider) -> list[Check]:
    info = await device_info(sp.lockdown)
    major = _major(info.ios_version)
    checks = [Check("pairing", "Mit diesem Rechner gekoppelt", OK,
                    f"{info.name} vertraut diesem Rechner.")]

    if major and major < 12:
        checks.append(Check("ios", "iOS-Version", BAD,
                            f"iOS {info.ios_version} ist zu alt - "
                            "ModStaller braucht iOS 12 oder neuer."))
    else:
        checks.append(Check("ios", "iOS-Version", OK,
                            f"iOS {info.ios_version} ({info.build})"))

    needs_dev_mode = major >= 16
    if not needs_dev_mode:
        checks.append(Check("developer-mode", "Entwicklermodus", NA,
                            "Vor iOS 16 nicht nötig."))
    elif info.developer_mode:
        checks.append(Check("developer-mode", "Entwicklermodus", OK, "an"))
    else:
        checks.append(Check(
            "developer-mode", "Entwicklermodus", BAD,
            "aus - sideloadete Apps starten nicht.",
            fix=FIX_DEVELOPER_MODE, fix_label="Einschalten",
            manual=DEVELOPER_MODE_HINT))

    checks.append(await _ddi_check(sp, major,
                                   ready=info.developer_mode or not needs_dev_mode))
    checks.append(await _profiles_check(sp))
    checks.append(await _space_check(sp))
    checks.append(Check("trust", "Entwickler vertrauen", INFO,
                        "Lässt sich nicht automatisieren.", manual=TRUST_HINT))
    return checks


async def _ddi_check(sp: ServiceProvider, major: int, *, ready: bool) -> Check:
    label = "Developer Disk Image"
    if not ready:
        return Check("ddi", label, NA,
                     "Erst nach dem Entwicklermodus - nur für JIT nötig.")
    from pymobiledevice3.services.mobile_image_mounter import (
        MobileImageMounterService,
    )
    image_type = "Personalized" if major >= 17 else "Developer"
    try:
        async with MobileImageMounterService(lockdown=sp.lockdown) as mounter:
            mounted = await mounter.is_image_mounted(image_type)
    except Exception as exc:
        return Check("ddi", label, INFO, f"Nicht abfragbar: {exc}")
    if mounted:
        return Check("ddi", label, OK, "geladen - JIT ist möglich.")
    return Check("ddi", label, INFO,
                 "Nicht geladen. Nur für JIT nötig; ModStaller lädt es dann "
                 "ohnehin selbst.",
                 fix=FIX_DDI, fix_label="Jetzt laden")


async def _profiles(sp: ServiceProvider):
    """Provisioning-Profile auf dem Geraet: lockdown zuerst, RSD als Rueckfall."""
    from pymobiledevice3.services.misagent import MisagentService
    try:
        async with MisagentService(sp.lockdown) as mis:
            return await mis.copy_all()
    except Exception:
        async with MisagentService(await sp.rsd()) as mis:
            return await mis.copy_all()


def _split_profiles(profiles) -> tuple[list, list]:
    now = datetime.now(timezone.utc)
    active, expired = [], []
    for p in profiles:
        exp = p.plist.get("ExpirationDate")
        if exp is not None and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        (expired if exp is not None and exp < now else active).append(p)
    return active, expired


async def _profiles_check(sp: ServiceProvider) -> Check:
    label = "App-Plätze"
    try:
        active, expired = _split_profiles(await _profiles(sp))
    except Exception as exc:
        return Check("profiles", label, INFO, f"Profile nicht lesbar: {exc}")

    detail = (f"{len(active)} aktive Entwickler-Profile auf dem iPhone "
              f"(Gratis-Accounts: höchstens {FREE_APP_LIMIT} Apps).")
    state = WARN if len(active) >= FREE_APP_LIMIT else OK
    if state == WARN:
        detail += " Bei einem Gratis-Account ist kein Platz frei."
    if expired:
        return Check("profiles", label, state,
                     f"{detail} {len(expired)} abgelaufene liegen noch herum.",
                     fix=FIX_EXPIRED_PROFILES,
                     fix_label="Abgelaufene entfernen")
    return Check("profiles", label, state, detail)


async def _space_check(sp: ServiceProvider) -> Check:
    try:
        usage = await sp.lockdown.get_value(domain="com.apple.disk_usage")
        free = int(usage["TotalDataAvailable"])
    except Exception:
        return Check("space", "Freier Speicher", INFO, "Nicht abfragbar.")
    if free < LOW_SPACE_BYTES:
        return Check("space", "Freier Speicher", WARN,
                     f"Nur noch {_gb(free)} frei - große Apps passen "
                     "womöglich nicht.")
    return Check("space", "Freier Speicher", OK, f"{_gb(free)} frei")


# -- Beheben -----------------------------------------------------------------


async def mount_developer_image(lockdown, on_step=lambda msg: None) -> None:
    """Laedt das passende Developer Disk Image, falls es noch fehlt."""
    from pymobiledevice3.exceptions import (
        AlreadyMountedError, DeveloperDiskImageNotFoundError,
    )
    from pymobiledevice3.services.mobile_image_mounter import auto_mount

    on_step("Developer Disk Image bereitstellen …")
    try:
        await auto_mount(lockdown)
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


async def run_fix(fix: str, udid: str | None = None, *,
                  on_step: Callable[[str], None] = lambda msg: None
                  ) -> FixResult:
    if fix == FIX_PAIR:
        return await _pair(udid, on_step)
    async with ServiceProvider(udid) as sp:
        if fix == FIX_DEVELOPER_MODE:
            return await _enable_developer_mode(sp, on_step)
        if fix == FIX_DDI:
            await mount_developer_image(sp.lockdown, on_step)
            return FixResult("Developer Disk Image ist geladen.")
        if fix == FIX_EXPIRED_PROFILES:
            return await _remove_expired_profiles(sp, on_step)
    raise DeviceError(f"Unbekannte Korrektur: {fix}")


async def _pair(udid: str | None, on_step) -> FixResult:
    from pymobiledevice3.exceptions import (
        PairingDialogResponsePendingError, PasswordRequiredError,
        UserDeniedPairingError,
    )
    from pymobiledevice3.lockdown import create_using_usbmux

    on_step("Am iPhone erscheint gleich „Diesem Computer vertrauen?“ - "
            "bitte „Vertrauen“ tippen und den Code eingeben …")
    try:
        lockdown = await create_using_usbmux(
            serial=udid, label="ModStaller", autopair=True,
            pair_timeout=PAIR_TIMEOUT)
    except UserDeniedPairingError as exc:
        raise DeviceError("Am iPhone wurde „Nicht vertrauen“ gewählt. "
                          "Einfach erneut versuchen.") from exc
    except PairingDialogResponsePendingError as exc:
        raise DeviceError("Am iPhone kam keine Antwort. iPhone entsperren "
                          "und erneut versuchen.") from exc
    except PasswordRequiredError as exc:
        raise DeviceError("Das iPhone ist gesperrt - bitte entsperren und "
                          "erneut versuchen.") from exc
    await lockdown.close()
    return FixResult("Gekoppelt - das iPhone vertraut diesem Rechner jetzt.")


async def _enable_developer_mode(sp: ServiceProvider, on_step) -> FixResult:
    from pymobiledevice3.exceptions import DeviceHasPasscodeSetError
    from pymobiledevice3.services.amfi import AmfiService

    amfi = AmfiService(sp.lockdown)
    on_step("Entwicklermodus anfordern …")
    try:
        on_step("Das iPhone startet gleich neu. Nicht abstecken - "
                "ModStaller bestätigt die Nachfrage danach selbst.")
        await asyncio.wait_for(amfi.enable_developer_mode(enable_post_restart=True),
                               DEVELOPER_MODE_TIMEOUT)
    except DeviceHasPasscodeSetError:
        # Mit Code-Sperre bleibt der Schalter dem Menschen vorbehalten. Wir
        # sorgen wenigstens dafuer, dass er in den Einstellungen auftaucht.
        on_step("Code-Sperre aktiv - der Schalter muss am iPhone umgelegt "
                "werden. Er wird jetzt in den Einstellungen eingeblendet.")
        await amfi.reveal_developer_mode_option_in_ui()
        return FixResult(
            "Wegen der Code-Sperre kann ModStaller den Entwicklermodus nicht "
            "selbst einschalten. Der Schalter ist jetzt in den Einstellungen "
            "sichtbar.",
            manual=DEVELOPER_MODE_HINT)
    except asyncio.TimeoutError as exc:
        raise DeviceError(
            "Das iPhone hat sich nach dem Neustart nicht zurückgemeldet. "
            "Entsperren, ggf. die Nachfrage „Entwicklermodus einschalten?“ "
            "selbst bestätigen und die Prüfung wiederholen.") from exc
    return FixResult("Entwicklermodus ist an.")


async def _remove_expired_profiles(sp: ServiceProvider, on_step) -> FixResult:
    from pymobiledevice3.services.misagent import MisagentService

    _, expired = _split_profiles(await _profiles(sp))
    if not expired:
        return FixResult("Keine abgelaufenen Profile gefunden.")
    async with MisagentService(sp.lockdown) as mis:
        for p in expired:
            name = p.plist.get("Name", p.plist.get("UUID", "?"))
            on_step(f"Entferne {name} …")
            await mis.remove(p.plist["UUID"])
    return FixResult(f"{len(expired)} abgelaufene(s) Profil(e) entfernt.")
