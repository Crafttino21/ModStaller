"""Connection to the iPhone: usbmux, lockdown and - where needed - the RSD
tunnel.

Since iOS 17, parts of the developer services have moved behind a CoreDevice
tunnel. ``com.apple.mobile.installation_proxy`` still accepts connections over
the classic usbmux link, but sometimes never answers an ``Install`` - the
service then has to be addressed as
``com.apple.mobile.installation_proxy.shim.remote`` via RSD.

Which route works on a given iOS is an empirical question. That is why
:func:`service_provider` tries lockdown first and falls back to the userspace
tunnel - it needs no root because it keeps the TCP stack inside the process.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from .. import config
from ..errors import DeviceNotFound, DeviceError, NotPaired, UsbServiceUnavailable
from ..i18n import _

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceInfo:
    udid: str
    name: str
    product_type: str
    ios_version: str
    build: str
    developer_mode: bool

    def __str__(self) -> str:
        dm = "on" if self.developer_mode else "OFF"
        return (f"{self.name} ({self.product_type}) - iOS {self.ios_version} "
                f"[{self.build}] - Developer Mode {dm}\n  UDID {self.udid}")


def usb_service_hint() -> str:
    """What to do when the Apple device service is missing (Windows)."""
    return _("ModStaller can set it up by itself (“modstaller usb-setup” or "
             "the button on the overview) - or install the “Apple Devices” "
             "app from the Microsoft Store.")


async def list_devices(*, posix: bool | None = None) -> list[str]:
    """Serials of the connected iPhones.

    Raises :class:`UsbServiceUnavailable` on Windows when the Apple device
    service does not answer - without it no iPhone is ever visible, even
    though Explorer shows one.
    """
    from pymobiledevice3.exceptions import ConnectionFailedToUsbmuxdError
    from pymobiledevice3.usbmux import list_devices as _ls

    if posix is None:
        posix = config.POSIX
    try:
        return [d.serial for d in await _ls()]
    except ConnectionFailedToUsbmuxdError as exc:
        if not posix:
            raise UsbServiceUnavailable(
                _("The Apple device service is not reachable.") + " "
                + usb_service_hint()) from exc
        # usbmuxd is socket-activated: without a device it isn't running.
        return []
    except Exception:
        # Not expected - and invisible unless we write it down.
        log.warning("Listing USB devices failed", exc_info=True)
        return []


async def connect(udid: str | None = None, *, timeout: float = 0.0):
    """Opens a lockdown connection, optionally waiting for one."""
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
        # Older systems don't know the switch - it doesn't exist there, and
        # that is not an error.
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
    level: int          # percent
    charging: bool


async def battery(lockdown) -> Battery | None:
    """Battery level - ``None`` if the device doesn't reveal it."""
    try:
        v = await lockdown.get_value(domain="com.apple.mobile.battery")
        return Battery(level=int(v["BatteryCurrentCapacity"]),
                       charging=bool(v.get("BatteryIsCharging")))
    except Exception:
        return None


class ServiceProvider:
    """Holds lockdown and - when needed - the RSD tunnel.

    Usage::

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
        """Sets up the userspace RSD tunnel (without root) and caches it."""
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
