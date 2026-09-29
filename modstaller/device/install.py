"""Getting an IPA onto the device.

Two routes, because iOS 17+ changed the rules:

* ``lockdown``  - the classic route via usbmux.
* ``rsd``       - via the CoreDevice tunnel, service name
  ``com.apple.mobile.installation_proxy.shim.remote``.

Which route works depends on the iOS version. We try lockdown first (faster,
no tunnel setup) and switch to RSD on errors. The route taken is reported
back so the caller can remember it and take the right one straight away next
time.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import re

from ..errors import DeviceError
from ..i18n import _

#: How long we wait for an install before considering it hung.
#: A hanging installation_proxy is the typical symptom of the service having
#: been addressed over the wrong transport.
INSTALL_TIMEOUT = 300.0


#: Apple's message when the device has reached its quota for free profiles.
#: It lists the occupied slots in plain text.
_APP_LIMIT = "maximum number of installed apps using a free developer profile"


def _slot_limit_message(text: str) -> str:
    """Turns Apple's raw text into a message one can actually act on."""
    installed = re.findall(r'"[A-Z0-9]+\.([^"]+)"', text)
    listing = "\n".join(f"    {b}" for b in installed)
    return (
        _("The iPhone has reached its limit: with a free Apple account at "
          "most three sideloaded apps may be installed at the same time.")
        + "\n\n"
        + (_("Taken by:\n{listing}", listing=listing) + "\n\n"
           if installed else "")
        + _("To free a slot:\n    modstaller uninstall <bundle-id>\nor "
            "delete the app on the iPhone itself.")
        + "\n\n"
        + _("Signing succeeded - the finished IPA stays around and is reused "
            "on the next attempt.")
    )


@dataclass
class InstallResult:
    bundle_id: str | None
    transport: str          # "lockdown" or "rsd"
    upgraded: bool


async def _installation_proxy(provider):
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    return InstallationProxyService(lockdown=provider)


async def uninstall_app(sp, bundle_id: str) -> str:
    """Removes an app and returns the transport that was used."""
    errors: list[str] = []
    for transport, provider in await _providers(sp):
        try:
            async with await _installation_proxy(provider) as ip:
                await ip.uninstall(bundle_id)
            return transport
        except Exception as exc:
            errors.append(f"{transport}: {type(exc).__name__}: {exc}")
    raise DeviceError(_("{bundle_id} could not be removed:", bundle_id=bundle_id)
                      + "\n  " + "\n  ".join(dict.fromkeys(errors)))


#: Signatures that Apple issues itself - neither is a sideload.
APP_STORE_SIGNER = "Apple iPhone OS Application Signing"
TESTFLIGHT_SIGNER = "TestFlight Beta Distribution"


def app_origin(meta: dict) -> dict:
    """Where an installed app comes from - based on its signature fields.

    Measured on a device (iOS 27, 150 apps): store apps carry Apple's store
    signature, TestFlight apps ``TestFlight Beta Distribution``, sideloaded
    ones a developer identity *and* ``get-task-allow`` in their
    entitlements. The team ID is only reliably found in the entitlements -
    the identity's name names the certificate holder, not the team.

    ``origin`` distinguishes four cases because "not from the store" would
    be too coarse: TestFlight would otherwise look like a sideload.
    ``developer`` is the sharpest statement - only those can run JIT, and
    only those expire after seven days. Enterprise-signed IPAs (``other``)
    are sideloaded too, but neither of the two.
    """
    ent = meta.get("Entitlements") or {}
    signer = str(meta.get("SignerIdentity", ""))
    if signer == APP_STORE_SIGNER:
        origin = "store"
    elif signer == TESTFLIGHT_SIGNER:
        origin = "testflight"
    elif ent.get("get-task-allow"):
        origin = "developer"
    else:
        origin = "other"
    return {
        "signer": signer,
        "teamId": str(ent.get("com.apple.developer.team-identifier", "")),
        "origin": origin,
        "sideloaded": origin in ("developer", "other"),
        "developerSigned": origin == "developer",
    }


async def list_apps(sp, *, user_only: bool = True) -> dict:
    """Installed apps. Also the cheapest test of whether
    installation_proxy answers at all on this iOS."""
    for transport, provider in await _providers(sp):
        try:
            async with await _installation_proxy(provider) as ip:
                return await ip.get_apps(
                    application_type="User" if user_only else "Any")
        except Exception as exc:
            last = exc
    raise DeviceError(_("installation_proxy does not answer: {error}",
                        error=last))


async def _providers(sp) -> list[tuple[str, object]]:
    """lockdown first, RSD as the fallback.

    A device reached only through its tunnel (Apple TV) has no lockdown -
    there the RSD is both."""
    if sp.lockdown is getattr(sp, "_rsd", None):
        return [("rsd", sp.lockdown)]
    out: list[tuple[str, object]] = [("lockdown", sp.lockdown)]
    try:
        out.append(("rsd", await sp.rsd()))
    except DeviceError:
        pass  # Without a tunnel, lockdown is the only route.
    return out


async def install_ipa(
    sp,
    ipa: Path,
    *,
    upgrade: bool = False,
    progress: Callable[[int], None] | None = None,
) -> InstallResult:
    """Installs an **already signed** IPA.

    ``developer=True`` sets ``PackageType=Developer`` - without it, iOS
    rejects an app signed with a development certificate.
    """
    ipa = Path(ipa)
    if not ipa.is_file():
        raise DeviceError(_("IPA not found: {path}", path=ipa))

    def handler(percent, *_):
        if progress:
            progress(int(percent))

    errors: list[str] = []
    for transport, provider in await _providers(sp):
        try:
            async with await _installation_proxy(provider) as ip:
                await asyncio.wait_for(
                    ip.install_from_local(
                        str(ipa),
                        cmd="Upgrade" if upgrade else "Install",
                        handler=handler,
                        developer=True,
                    ),
                    timeout=INSTALL_TIMEOUT,
                )
            return InstallResult(bundle_id=None, transport=transport,
                                 upgraded=upgrade)
        except asyncio.TimeoutError:
            errors.append(_(
                "{transport}: installation_proxy did not answer within "
                "{seconds:.0f}s (the service accepts the connection but does "
                "not answer the install)",
                transport=transport, seconds=INSTALL_TIMEOUT))
        except Exception as exc:
            errors.append(f"{transport}: {type(exc).__name__}: {exc}")

    # Device-side rejections hit every transport alike. Showing them twice
    # only hides the fact that it isn't a transport problem at all.
    joined = " ".join(errors)
    if _APP_LIMIT in joined:
        raise DeviceError(_slot_limit_message(joined))

    unique = list(dict.fromkeys(errors))
    raise DeviceError(
        "Installation failed:\n  " + "\n  ".join(unique)
    )
