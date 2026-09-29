"""The RSD tunnel - without root, over any way to the device.

From iOS 17 on, developer services (Developer Disk Image, JIT, sometimes the
installation) sit behind a CoreDevice tunnel. pymobiledevice3 builds it in
userspace: a TCP stack inside this process, no TUN device, no admin rights.

Its own :class:`UserspaceRsdTunnel` insists on usbmux for the first step.
That is fine for the cable, but an Apple TV has no cable and an iPhone in
the Wi-Fi is reached over plain TCP. So the tunnel is built here from any
*tunnel service*:

* ``CoreDeviceTunnelProxy`` over an open lockdown - iOS 17.4 and newer, on
  the cable as well as over Wi-Fi;
* ``RemotePairingTunnelService`` - the Apple TV, and iPhones below 17.4.

The steps are exactly those of ``UserspaceRsdTunnel._aopen_locked``; the
class below inherits its teardown, so both keep working together.

pymobiledevice3 allows **one** such tunnel per process (its TCP stack is a
process-wide singleton) and guards that per event loop only. The server runs
every job in its own thread with its own loop, so a process-wide lock sits
on top here.
"""

from __future__ import annotations

import asyncio
import threading
from contextlib import AsyncExitStack
from typing import Awaitable, Callable

from ..errors import DeviceError
from ..i18n import _

#: How long a second job waits for the tunnel of the first.
TUNNEL_WAIT = 120.0

_LOCK = threading.Lock()


async def _acquire() -> None:
    ok = await asyncio.to_thread(_LOCK.acquire, True, TUNNEL_WAIT)
    if not ok:
        raise DeviceError(_("Another operation is still using the connection to a "
                            "device. Try again once it has finished."))


class Tunnel:
    """One open tunnel and its RSD. ``await open()`` / ``await close()``."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self._held = False

    async def open(self):
        await _acquire()
        self._held = True
        try:
            return await self._inner.aopen()
        except BaseException:
            self._release()
            raise

    async def close(self) -> None:
        try:
            await self._inner.aclose()
        finally:
            self._release()

    def _release(self) -> None:
        if self._held:
            self._held = False
            _LOCK.release()


#: Builds the tunnel service. Returns it plus whatever else has to stay open
#: while the tunnel lives (a lockdown connection, say) and be closed after.
ProviderFactory = Callable[[], Awaitable[tuple[object, list]]]


def _provider_tunnel_class():
    from pymobiledevice3.remote import tunnel_service
    from pymobiledevice3.remote import userspace_tunnel as ut
    from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService

    class ProviderTunnel(ut.UserspaceRsdTunnel):
        def __init__(self, make_provider: ProviderFactory) -> None:
            super().__init__(serial=None)
            self._make_provider = make_provider

        async def _aopen_locked(self):
            if ut._active_tunnel is not None:
                raise DeviceError(_("Another operation is still using the connection "
                                    "to a device. Try again once it has finished."))
            tunnel_service.USE_USERSPACE_TUNNEL = True
            stack = AsyncExitStack()
            try:
                provider, keep_open = await self._make_provider()
                stack.push_async_callback(provider.close)
                for obj in keep_open:
                    stack.push_async_callback(obj.close)
                result = await stack.enter_async_context(provider.start_tcp_tunnel())
                self.tun = result.client.tun
                self.tun.set_peer(result.address)
                dial_plane = await stack.enter_async_context(
                    ut.UserspaceDialPlane(self.tun, result.address))
                rsd = RemoteServiceDiscoveryService(
                    (result.address, result.port), open_connection=dial_plane.dial,
                    auxiliary_metadata=getattr(result, "auxiliary_metadata", None))
                stack.push_async_callback(rsd.close)
                await rsd.connect()
            except BaseException:
                await stack.aclose()
                tunnel_service.USE_USERSPACE_TUNNEL = False
                self.tun = None
                raise
            self._exit_stack = stack
            self.rsd = rsd
            ut._active_tunnel = self
            ut.USERSPACE_ACTIVE = True
            self._transport_watcher = asyncio.create_task(
                self._watch_transport_closed(result.client))
            return rsd

    return ProviderTunnel


def usb_tunnel(udid: str | None) -> Tunnel:
    """The cable: pymobiledevice3's own way, unchanged - it has proven itself."""
    from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel
    return Tunnel(UserspaceRsdTunnel(udid))


def provider_tunnel(make_provider: ProviderFactory) -> Tunnel:
    return Tunnel(_provider_tunnel_class()(make_provider))


def core_device_proxy(lockdown) -> ProviderFactory:
    """iOS 17.4+: the tunnel service behind an already open lockdown (TCP or
    usbmux). Raises ``InvalidServiceError`` below 17.4."""
    async def make():
        from pymobiledevice3.remote.tunnel_service import CoreDeviceTunnelProxy
        return await CoreDeviceTunnelProxy.create(lockdown), []
    return make


def remote_pairing(identifier: str, host: str, port: int) -> ProviderFactory:
    """A device paired by RemotePairing, found by Bonjour at ``host:port``."""
    async def make():
        from pymobiledevice3.remote.tunnel_service import (
            create_core_device_tunnel_service_using_remotepairing,
        )
        service = await create_core_device_tunnel_service_using_remotepairing(
            identifier, host, port, autopair=False)
        return service, []
    return make
