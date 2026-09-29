"""Wi-Fi for an iPhone: once over the cable, afterwards without it.

Apple lets a computer become "trusted" only over USB. What that pairing
produces - the pair record - is just as good over the network, if the iPhone
allows connections there (lockdown's ``EnableWifiConnections``, the same
switch Finder/iTunes flip for "Show this iPhone when on Wi-Fi").

Switching on therefore needs the cable once:

1. set ``EnableWifiConnections``;
2. keep the pair record (``registry``) - lockdown over TCP needs it passed
   in, it cannot look it up by an IP address;
3. note the Wi-Fi MAC address - it names the iPhone in its Bonjour advert;
4. iOS 17 and newer: additionally pair RemotePairing over the cable. That is
   promptless there and gives the developer tunnel over Wi-Fi on iOS
   17.0-17.3, where lockdown has no tunnel proxy yet. From 17.4 on it is
   only the fallback.

Afterwards the background search (``discovery.NetworkScanner``) finds the
iPhone in the network and every action can use it.
"""

from __future__ import annotations

import logging
from typing import Callable

from ..errors import DeviceError
from ..i18n import _
from . import discovery, registry
from .connection import ServiceProvider

log = logging.getLogger(__name__)


def _major(version: str) -> int:
    try:
        return int(str(version).split(".")[0])
    except ValueError:
        return 0


async def _pair_record(lockdown, udid: str) -> dict | None:
    record = getattr(lockdown, "pair_record", None)
    if record:
        return dict(record)
    from pymobiledevice3.common import get_home_folder
    from pymobiledevice3.pair_records import get_preferred_pair_record
    return await get_preferred_pair_record(udid, get_home_folder())


async def _pair_remote(lockdown, on_step) -> bool:
    """RemotePairing over the cable (iOS 17+). No prompt on the iPhone."""
    from pymobiledevice3.exceptions import RemotePairingCompletedError
    from pymobiledevice3.remote.tunnel_service import RemotePairingLockdownService

    on_step(_("Setting up the developer tunnel for Wi-Fi …"))
    service = await RemotePairingLockdownService.create(lockdown)
    try:
        await service.connect(autopair=True)
    except RemotePairingCompletedError:
        pass        # paired just now - the record is written
    finally:
        await service.close()
    return True


async def enable(udid: str | None = None, *,
                 on_step: Callable[[str], None] = lambda msg: None) -> dict:
    """Switches on Wi-Fi for the iPhone on the cable. Returns what it did."""
    async with ServiceProvider(udid) as sp:
        if sp.transport != discovery.USB:
            raise DeviceError(_("Switching on Wi-Fi needs the iPhone on the USB cable "
                                "once - Apple only allows the pairing there."))
        lockdown = sp.lockdown
        values = getattr(lockdown, "all_values", None) or await lockdown.get_value()
        udid = sp.udid
        product = values.get("ProductType", "")
        version = values.get("ProductVersion", "")
        if registry.platform_for(product, values.get("DeviceClass", "")) == registry.TVOS:
            raise DeviceError(_("An Apple TV is paired by PIN, not over the cable."))

        on_step(_("Allowing connections over Wi-Fi …"))
        await lockdown.set_enable_wifi_connections(True)

        record = await _pair_record(lockdown, udid)
        if not record:
            raise DeviceError(_("The pairing with this computer could not be read. "
                                "Unplug the iPhone, plug it in again and retry."))
        registry.save_pair_record(udid, record)

        remote_identifier = ""
        if _major(version) >= 17:
            try:
                if await _pair_remote(lockdown, on_step):
                    remote_identifier = udid
            except Exception as exc:
                # Not fatal: from 17.4 on the tunnel goes through lockdown.
                log.warning("RemotePairing over USB failed: %s", exc)
                on_step(_("Developer tunnel over Wi-Fi not available: {error}", error=exc))

        registry.remember(
            udid, name=values.get("DeviceName", ""), product_type=product,
            os_version=version, platform=registry.IOS,
            wifi_mac=(values.get("WiFiAddress") or record.get("WiFiMACAddress") or ""),
            remote_identifier=remote_identifier, wifi_enabled=True)
    if discovery.SCANNER is not None:
        discovery.SCANNER.poke()
    return {"udid": udid, "tunnel": bool(remote_identifier) or _major(version) >= 17}


async def disable(udid: str, *, on_step: Callable[[str], None] = lambda msg: None) -> dict:
    """Switches Wi-Fi off again - on the iPhone too, if it is reachable."""
    known = registry.get(udid)
    if known is None:
        raise DeviceError(_("ModStaller does not know this device."))
    told_device = False
    try:
        async with ServiceProvider(udid) as sp:
            if sp.lockdown is not getattr(sp, "_rsd", None):
                on_step(_("Switching off connections over Wi-Fi …"))
                await sp.lockdown.set_enable_wifi_connections(False)
                told_device = True
    except Exception as exc:
        log.info("Wi-Fi off: device not reachable (%s) - only forgetting it", exc)
    registry.remember(udid, wifi_enabled=False, clear=("remote_identifier", "last_host"))
    registry.pair_record_path(udid).unlink(missing_ok=True)
    if discovery.SCANNER is not None:
        discovery.SCANNER.forget(udid)
    return {"udid": udid, "deviceUpdated": told_device}
