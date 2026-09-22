"""IPA auf das Geraet bringen.

Zwei Wege, weil iOS 17+ die Regeln geaendert hat:

* ``lockdown``  - der klassische Weg ueber usbmux.
* ``rsd``       - ueber den CoreDevice-Tunnel, Dienstname
  ``com.apple.mobile.installation_proxy.shim.remote``.

Welcher Weg traegt, haengt an der iOS-Version. Wir probieren lockdown zuerst
(schneller, kein Tunnel-Aufbau) und wechseln bei Fehlern auf RSD. Das Ergebnis
wird zurueckgemeldet, damit der Aufrufer es merken und beim naechsten Mal
direkt den richtigen Weg nehmen kann.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..errors import DeviceError

#: Wie lange wir auf ein Install warten, bevor wir es als haengend ansehen.
#: Ein haengendes installation_proxy ist das typische Symptom dafuer, dass der
#: Dienst ueber den falschen Transport angesprochen wurde.
INSTALL_TIMEOUT = 300.0


@dataclass
class InstallResult:
    bundle_id: str | None
    transport: str          # "lockdown" oder "rsd"
    upgraded: bool


async def _installation_proxy(provider):
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    return InstallationProxyService(lockdown=provider)


async def list_apps(sp, *, user_only: bool = True) -> dict:
    """Installierte Apps. Zugleich der guenstigste Test, ob
    installation_proxy auf diesem iOS ueberhaupt antwortet."""
    for transport, provider in await _providers(sp):
        try:
            async with await _installation_proxy(provider) as ip:
                return await ip.get_apps(
                    application_type="User" if user_only else "Any")
        except Exception as exc:
            last = exc
    raise DeviceError(f"installation_proxy antwortet nicht: {last}")


async def _providers(sp) -> list[tuple[str, object]]:
    """lockdown zuerst, RSD als Rueckfallebene."""
    out: list[tuple[str, object]] = [("lockdown", sp.lockdown)]
    try:
        out.append(("rsd", await sp.rsd()))
    except DeviceError:
        pass  # Ohne Tunnel bleibt lockdown der einzige Weg.
    return out


async def install_ipa(
    sp,
    ipa: Path,
    *,
    upgrade: bool = False,
    progress: Callable[[int], None] | None = None,
) -> InstallResult:
    """Installiert eine **bereits signierte** IPA.

    ``developer=True`` setzt ``PackageType=Developer`` - ohne das lehnt iOS
    eine mit Development-Zertifikat signierte App ab.
    """
    ipa = Path(ipa)
    if not ipa.is_file():
        raise DeviceError(f"IPA nicht gefunden: {ipa}")

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
            errors.append(
                f"{transport}: installation_proxy hat {INSTALL_TIMEOUT:.0f}s "
                f"nicht geantwortet (Dienst nimmt die Verbindung an, "
                f"beantwortet den Install aber nicht)"
            )
        except Exception as exc:
            errors.append(f"{transport}: {type(exc).__name__}: {exc}")

    raise DeviceError(
        "Installation ueber alle Transportwege fehlgeschlagen:\n  "
        + "\n  ".join(errors)
    )
