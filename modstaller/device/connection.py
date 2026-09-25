"""Verbindung zum iPhone: usbmux, lockdown und - wo noetig - der RSD-Tunnel.

Ab iOS 17 sind Teile der Entwickler-Dienste hinter einen CoreDevice-Tunnel
gewandert. ``com.apple.mobile.installation_proxy`` nimmt ueber die klassische
usbmux-Verbindung zwar noch Verbindungen an, beantwortet ein ``Install`` aber
teilweise nie - der Dienst muss dann als
``com.apple.mobile.installation_proxy.shim.remote`` ueber RSD angesprochen
werden.

Welcher Weg auf einem konkreten iOS geht, ist eine empirische Frage. Deshalb
probiert :func:`service_provider` lockdown zuerst und faellt auf den
Userspace-Tunnel zurueck - der braucht kein root, weil er den TCP-Stack im
Prozess selbst haelt.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..errors import DeviceNotFound, DeviceError, NotPaired
from ..i18n import _


@dataclass(frozen=True)
class DeviceInfo:
    udid: str
    name: str
    product_type: str
    ios_version: str
    build: str
    developer_mode: bool

    def __str__(self) -> str:
        dm = "an" if self.developer_mode else "AUS"
        return (f"{self.name} ({self.product_type}) - iOS {self.ios_version} "
                f"[{self.build}] - Developer Mode {dm}\n  UDID {self.udid}")


async def list_devices() -> list[str]:
    from pymobiledevice3.usbmux import list_devices as _ls
    try:
        return [d.serial for d in await _ls()]
    except Exception:
        # usbmuxd ist socket-aktiviert: ohne Geraet laeuft es gar nicht.
        return []


async def connect(udid: str | None = None, *, timeout: float = 0.0):
    """Oeffnet eine lockdown-Verbindung, optional wartend."""
    from pymobiledevice3.exceptions import (
        NotPairedError, PasswordRequiredError, ConnectionFailedError,
    )
    from pymobiledevice3.lockdown import create_using_usbmux

    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            return await create_using_usbmux(serial=udid, label="ModStaller")
        except NotPairedError as exc:
            raise NotPaired(_(
                "The device is not paired with this computer. Unlock the "
                "iPhone, plug in USB, confirm ‘Trust’ and try again - "
                "pairing then happens on its own.")) from exc
        except PasswordRequiredError as exc:
            raise NotPaired(_(
                "The iPhone is locked. Please unlock it and try again."
            )) from exc
        except (ConnectionFailedError, OSError) as exc:
            if asyncio.get_running_loop().time() >= deadline:
                raise DeviceNotFound(_(
                    "No iPhone found. Connect it via USB and unlock it. "
                    "(usbmuxd only starts once a device is present.)"
                )) from exc
            await asyncio.sleep(0.5)


async def device_info(lockdown) -> DeviceInfo:
    v = await lockdown.get_value()
    dev_mode = False
    try:
        dev_mode = bool(await lockdown.get_developer_mode_status())
    except Exception:
        # Aeltere Systeme kennen den Schalter nicht - dort gibt es ihn nicht,
        # und das ist kein Fehler.
        pass
    return DeviceInfo(
        udid=v.get("UniqueDeviceID", ""),
        name=v.get("DeviceName", "?"),
        product_type=v.get("ProductType", "?"),
        ios_version=v.get("ProductVersion", "?"),
        build=v.get("BuildVersion", "?"),
        developer_mode=dev_mode,
    )


@dataclass(frozen=True)
class Battery:
    level: int          # Prozent
    charging: bool


async def battery(lockdown) -> Battery | None:
    """Akkustand - ``None``, wenn das Geraet ihn nicht verraet."""
    try:
        v = await lockdown.get_value(domain="com.apple.mobile.battery")
        return Battery(level=int(v["BatteryCurrentCapacity"]),
                       charging=bool(v.get("BatteryIsCharging")))
    except Exception:
        return None


class ServiceProvider:
    """Haelt lockdown und - bei Bedarf - den RSD-Tunnel.

    Nutzung::

        async with ServiceProvider(udid) as sp:
            provider = await sp.for_installation()
    """

    def __init__(self, udid: str | None = None) -> None:
        self.udid = udid
        self.lockdown = None
        self._tunnel = None
        self._rsd = None

    async def __aenter__(self) -> "ServiceProvider":
        self.lockdown = await connect(self.udid)
        self.udid = getattr(self.lockdown, "udid", None) or self.udid
        return self

    async def __aexit__(self, *exc) -> None:
        if self._tunnel is not None:
            try:
                await self._tunnel.close()
            except Exception:
                pass
        if self.lockdown is not None:
            try:
                await self.lockdown.close()
            except Exception:
                pass

    async def rsd(self):
        """Baut den Userspace-RSD-Tunnel auf (ohne root) und cached ihn."""
        if self._rsd is not None:
            return self._rsd
        from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel

        try:
            self._tunnel = UserspaceRsdTunnel(self.udid)
            self._rsd = await self._tunnel.__aenter__()
        except Exception as exc:
            raise DeviceError(_(
                "RSD tunnel could not be established: {error}\nFrom iOS 17 "
                "on, installing apps needs this tunnel. Often helps: unlock "
                "the iPhone, re-plug the cable.", error=exc)) from exc
        return self._rsd
