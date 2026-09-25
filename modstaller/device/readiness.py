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
from ..i18n import _
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

#: Erst beim Abruf uebersetzen - beim Import steht die Sprache noch nicht fest.
TRUST_HINT = (
    "When an app is started for the first time: Settings › General › VPN & "
    "Device Management › your Apple ID › “Trust”. Once per certificate."
)
DEVELOPER_MODE_HINT = (
    "Settings › Privacy & Security › turn on Developer Mode. The iPhone "
    "restarts; then confirm “Turn On” and enter the passcode."
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
            return [Check("pairing", _("iPhone unlocked"), BAD,
                          _("The iPhone is locked."),
                          manual=_("Unlock the iPhone - the check then "
                                   "continues on its own."))]
        return [Check("pairing", _("Paired with this computer"), BAD,
                      _("The iPhone does not trust this computer yet."),
                      fix=FIX_PAIR, fix_label=_("Request pairing"),
                      manual=_("Tap “Trust” on the iPhone and enter the "
                               "passcode."))]


async def _checks(sp: ServiceProvider) -> list[Check]:
    info = await device_info(sp.lockdown)
    major = _major(info.ios_version)
    checks = [Check("pairing", _("Paired with this computer"), OK,
                    _("{name} trusts this computer.", name=info.name))]

    if major and major < 12:
        checks.append(Check("ios", _("iOS version"), BAD,
                            _("iOS {version} is too old - ModStaller needs "
                              "iOS 12 or newer.", version=info.ios_version)))
    else:
        checks.append(Check("ios", _("iOS version"), OK,
                            f"iOS {info.ios_version} ({info.build})"))

    needs_dev_mode = major >= 16
    if not needs_dev_mode:
        checks.append(Check("developer-mode", _("Developer Mode"), NA,
                            _("Not needed before iOS 16.")))
    elif info.developer_mode:
        checks.append(Check("developer-mode", _("Developer Mode"), OK,
                            _("on")))
    else:
        checks.append(Check(
            "developer-mode", _("Developer Mode"), BAD,
            _("off - sideloaded apps will not start."),
            fix=FIX_DEVELOPER_MODE, fix_label=_("Turn on"),
            manual=_(DEVELOPER_MODE_HINT)))

    checks.append(await _ddi_check(sp, major,
                                   ready=info.developer_mode or not needs_dev_mode))
    checks.append(await _profiles_check(sp))
    checks.append(await _space_check(sp))
    checks.append(Check("trust", _("Trust developer"), INFO,
                        _("Cannot be automated."), manual=_(TRUST_HINT)))
    return checks


async def _ddi_check(sp: ServiceProvider, major: int, *, ready: bool) -> Check:
    label = "Developer Disk Image"
    if not ready:
        return Check("ddi", label, NA,
                     _("Only after Developer Mode - needed for JIT only."))
    from pymobiledevice3.services.mobile_image_mounter import (
        MobileImageMounterService,
    )
    image_type = "Personalized" if major >= 17 else "Developer"
    try:
        async with MobileImageMounterService(lockdown=sp.lockdown) as mounter:
            mounted = await mounter.is_image_mounted(image_type)
    except Exception as exc:
        return Check("ddi", label, INFO,
                     _("Cannot be queried: {error}", error=exc))
    if mounted:
        return Check("ddi", label, OK, _("mounted - JIT is possible."))
    return Check("ddi", label, INFO,
                 _("Not mounted. Needed for JIT only; ModStaller mounts it "
                   "itself when required."),
                 fix=FIX_DDI, fix_label=_("Mount now"))


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
    label = _("App slots")
    try:
        active, expired = _split_profiles(await _profiles(sp))
    except Exception as exc:
        return Check("profiles", label, INFO,
                     _("Profiles not readable: {error}", error=exc))

    detail = _("{count} active developer profiles on the iPhone "
               "(free accounts: at most {limit} apps).",
               count=len(active), limit=FREE_APP_LIMIT)
    state = WARN if len(active) >= FREE_APP_LIMIT else OK
    if state == WARN:
        detail += " " + _("With a free account no slot is left.")
    if expired:
        return Check("profiles", label, state,
                     detail + " " + _("{count} expired ones are still lying "
                                      "around.", count=len(expired)),
                     fix=FIX_EXPIRED_PROFILES,
                     fix_label=_("Remove expired"))
    return Check("profiles", label, state, detail)


async def _space_check(sp: ServiceProvider) -> Check:
    try:
        usage = await sp.lockdown.get_value(domain="com.apple.disk_usage")
        free = int(usage["TotalDataAvailable"])
    except Exception:
        return Check("space", _("Free storage"), INFO,
                     _("Cannot be queried."))
    if free < LOW_SPACE_BYTES:
        return Check("space", _("Free storage"), WARN,
                     _("Only {size} left - large apps may not fit.",
                       size=_gb(free)))
    return Check("space", _("Free storage"), OK,
                 _("{size} free", size=_gb(free)))


# -- Beheben -----------------------------------------------------------------


async def mount_developer_image(lockdown, on_step=lambda msg: None) -> None:
    """Laedt das passende Developer Disk Image, falls es noch fehlt."""
    from pymobiledevice3.exceptions import (
        AlreadyMountedError, DeveloperDiskImageNotFoundError,
    )
    from pymobiledevice3.services.mobile_image_mounter import auto_mount

    on_step(_("Preparing Developer Disk Image …"))
    try:
        await auto_mount(lockdown)
    except AlreadyMountedError:
        pass
    except DeveloperDiskImageNotFoundError as exc:
        raise DeviceError(_(
            "No matching Developer Disk Image found - for very new iOS "
            "versions there is none yet. ({error})", error=exc)) from exc
    except Exception as exc:
        raise DeviceError(_(
            "Developer Disk Image could not be mounted: {error}",
            error=exc or type(exc).__name__)) from exc


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
            return FixResult(_("Developer Disk Image is mounted."))
        if fix == FIX_EXPIRED_PROFILES:
            return await _remove_expired_profiles(sp, on_step)
    raise DeviceError(_("Unknown fix: {fix}", fix=fix))


async def _pair(udid: str | None, on_step) -> FixResult:
    from pymobiledevice3.exceptions import (
        PairingDialogResponsePendingError, PasswordRequiredError,
        UserDeniedPairingError,
    )
    from pymobiledevice3.lockdown import create_using_usbmux

    on_step(_("The iPhone will ask “Trust This Computer?” in a moment - "
              "please tap “Trust” and enter the passcode …"))
    try:
        lockdown = await create_using_usbmux(
            serial=udid, label="ModStaller", autopair=True,
            pair_timeout=PAIR_TIMEOUT)
    except UserDeniedPairingError as exc:
        raise DeviceError(_("“Don’t Trust” was chosen on the iPhone. "
                            "Just try again.")) from exc
    except PairingDialogResponsePendingError as exc:
        raise DeviceError(_("No answer from the iPhone. Unlock it and try "
                            "again.")) from exc
    except PasswordRequiredError as exc:
        raise DeviceError(_("The iPhone is locked - please unlock it and try "
                            "again.")) from exc
    await lockdown.close()
    return FixResult(_("Paired - the iPhone trusts this computer now."))


async def _enable_developer_mode(sp: ServiceProvider, on_step) -> FixResult:
    from pymobiledevice3.exceptions import DeviceHasPasscodeSetError
    from pymobiledevice3.services.amfi import AmfiService

    amfi = AmfiService(sp.lockdown)
    on_step(_("Requesting Developer Mode …"))
    try:
        on_step(_("The iPhone will restart in a moment. Do not unplug it - "
                  "ModStaller confirms the prompt afterwards itself."))
        await asyncio.wait_for(amfi.enable_developer_mode(enable_post_restart=True),
                               DEVELOPER_MODE_TIMEOUT)
    except DeviceHasPasscodeSetError:
        # Mit Code-Sperre bleibt der Schalter dem Menschen vorbehalten. Wir
        # sorgen wenigstens dafuer, dass er in den Einstellungen auftaucht.
        on_step(_("Passcode set - the switch has to be flipped on the iPhone. "
                  "It is now shown in Settings."))
        await amfi.reveal_developer_mode_option_in_ui()
        return FixResult(
            _("Because a passcode is set, ModStaller cannot turn on Developer "
              "Mode itself. The switch is now visible in Settings."),
            manual=_(DEVELOPER_MODE_HINT))
    except asyncio.TimeoutError as exc:
        raise DeviceError(_(
            "The iPhone did not report back after the restart. Unlock it, "
            "confirm the “Turn on Developer Mode?” prompt yourself if "
            "needed, and run the check again.")) from exc
    return FixResult(_("Developer Mode is on."))


async def _remove_expired_profiles(sp: ServiceProvider, on_step) -> FixResult:
    from pymobiledevice3.services.misagent import MisagentService

    _, expired = _split_profiles(await _profiles(sp))
    if not expired:
        return FixResult(_("No expired profiles found."))
    async with MisagentService(sp.lockdown) as mis:
        for p in expired:
            name = p.plist.get("Name", p.plist.get("UUID", "?"))
            on_step(_("Removing {name} …", name=name))
            await mis.remove(p.plist["UUID"])
    return FixResult(_("Removed {count} expired profile(s).",
                       count=len(expired)))
