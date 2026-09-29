"""Connection to the device: usbmux, lockdown over TCP, and - where needed -
the RSD tunnel.

Since iOS 17, parts of the developer services have moved behind a CoreDevice
tunnel. ``com.apple.mobile.installation_proxy`` still accepts connections over
the classic usbmux link, but sometimes never answers an ``Install`` - the
service then has to be addressed as
``com.apple.mobile.installation_proxy.shim.remote`` via RSD.

Which route works on a given iOS is an empirical question. That is why
callers try lockdown first and fall back to the userspace tunnel - it needs
no root because it keeps the TCP stack inside the process.

The way to the device (see :mod:`.discovery`) is the cable, usbmuxd's
network devices, lockdown over TCP in the Wi-Fi, or - for an Apple TV - a
RemotePairing tunnel only. For the last one there is no lockdown connection
at all: :attr:`ServiceProvider.lockdown` is then the RSD itself, which the
pymobiledevice3 services accept in its place.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from .. import config
from ..errors import (
    DeviceNotFound, DeviceError, NotPaired, UsbServiceUnavailable, WifiPairingInvalid,
)
from ..i18n import _
from . import discovery, registry
from .discovery import REMOTE, USB, USBMUX_NET, WIFI, DeviceRef, usb_service_hint

log = logging.getLogger(__name__)

#: How long lockdown over Wi-Fi may take to answer.
WIFI_CONNECT_TIMEOUT = 10.0
#: Tries per tunnel way over the network, and the pause between them.
NETWORK_TUNNEL_ATTEMPTS = 3
NETWORK_RETRY_PAUSE = 1.5

__all__ = [
    "DeviceInfo", "Battery", "ServiceProvider", "battery", "connect", "device_info",
    "get_value", "list_devices", "resolve", "usb_service_hint",
]


@dataclass(frozen=True)
class DeviceInfo:
    udid: str
    name: str
    product_type: str
    #: The OS version - iOS or tvOS. The name stayed for the callers.
    ios_version: str
    build: str
    developer_mode: bool
    platform: str = registry.IOS
    transport: str = USB

    @property
    def os_name(self) -> str:
        return {registry.TVOS: "tvOS", registry.XROS: "visionOS"}.get(self.platform, "iOS")

    @property
    def kind(self) -> str:
        from .models import device_kind
        return device_kind(self.product_type)

    def __str__(self) -> str:
        dm = "on" if self.developer_mode else "OFF"
        return (f"{self.name} ({self.product_type}) - {self.os_name} {self.ios_version} "
                f"[{self.build}] - Developer Mode {dm} - {self.transport}\n  UDID {self.udid}")


async def list_devices(*, posix: bool | None = None) -> list[str]:
    """UDIDs of the devices usbmuxd lists - cable and network alike.

    Raises :class:`UsbServiceUnavailable` on Windows when the Apple device
    service does not answer - without it no iPhone is ever visible, even
    though Explorer shows one.
    """
    return [r.udid for r in await discovery.usbmux_refs(posix=posix)]


def _not_found() -> DeviceNotFound:
    return DeviceNotFound(_(
        "No device found. Connect the iPhone via USB and unlock it - or, once "
        "Wi-Fi is switched on for it in ModStaller, bring it into the same "
        "network. (usbmuxd only starts once a device is present.)"))


async def resolve(udid: str | None = None) -> DeviceRef:
    """The best way to ``udid`` right now - or to the default device.

    Default: the configured ``default_udid`` if it is reachable, else the
    first device (the cable comes first).
    """
    refs = await discovery.attached()
    if udid:
        for ref in refs:
            if ref.udid == udid:
                return ref
        # A known network device the background search just missed (its
        # adverts come and go with the device's sleep): look once more.
        known = registry.get(udid)
        if known is not None and (known.wifi_enabled or known.remote_identifier):
            found = await discovery.NetworkScanner().scan()
            if discovery.SCANNER is not None:
                discovery.SCANNER._record(found)
            hit = discovery.merge(found)
            for ref in hit:
                if ref.udid == udid:
                    return ref
        raise _not_found()
    if not refs:
        raise _not_found()
    preferred = config.Settings.load().default_udid
    if preferred:
        for ref in refs:
            if ref.udid == preferred:
                return ref
    return refs[0]


async def connect(udid: str | None = None, *, timeout: float = 0.0,
                  ref: DeviceRef | None = None):
    """Opens a lockdown connection, optionally waiting for one.

    Not for a pure RemotePairing device (transport ``remote``) - that one
    only has the tunnel, see :class:`ServiceProvider`.
    """
    from pymobiledevice3.exceptions import (
        NotPairedError, PasswordRequiredError, ConnectionFailedError,
    )

    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            target = ref or await resolve(udid)
            return await _open_lockdown(target)
        except NotPairedError as exc:
            raise NotPaired(_(
                "The device is not paired with this computer. Unlock the "
                "iPhone, plug in USB, confirm ‘Trust’ and try again - "
                "pairing then happens on its own.")) from exc
        except PasswordRequiredError as exc:
            raise NotPaired(_(
                "The iPhone is locked. Please unlock it and try again."
            )) from exc
        except (DeviceNotFound, ConnectionFailedError, OSError) as exc:
            if asyncio.get_running_loop().time() >= deadline:
                if isinstance(exc, DeviceNotFound):
                    raise
                raise _not_found() from exc
            ref = None       # maybe it comes back over another way
            await asyncio.sleep(0.5)


async def _open_lockdown(ref: DeviceRef):
    from pymobiledevice3.lockdown import create_using_tcp, create_using_usbmux

    if ref.transport == REMOTE:
        raise DeviceError(_("This device can only be reached through its tunnel."))
    if ref.transport == WIFI:
        record = registry.load_pair_record(ref.udid)
        if record is None:
            raise WifiPairingInvalid(_(
                "ModStaller has no Wi-Fi pairing for this iPhone yet. Connect "
                "it via USB once and switch on Wi-Fi for it."))
        # Bounded: a sleeping iPhone may not answer at all, and TCP would
        # wait minutes before giving up.
        lockdown = await asyncio.wait_for(
            create_using_tcp(hostname=ref.host, pair_record=record,
                             autopair=False, label="ModStaller"),
            WIFI_CONNECT_TIMEOUT)
        if not lockdown.paired:
            await lockdown.close()
            raise WifiPairingInvalid(_(
                "The iPhone no longer accepts the Wi-Fi pairing. Connect it "
                "via USB once and switch on Wi-Fi for it again."))
        return lockdown
    return await create_using_usbmux(
        serial=ref.udid, label="ModStaller",
        connection_type="Network" if ref.transport == USBMUX_NET else "USB")


async def get_value(provider, domain: str | None = None, key: str | None = None):
    """``get_value`` on a lockdown client - or on the lockdown behind an RSD,
    which has none of its own. Without either, what the RSD handshake told."""
    if hasattr(provider, "get_value"):
        return await provider.get_value(domain=domain, key=key)
    inner = getattr(provider, "lockdown", None)
    if inner is not None:
        return await inner.get_value(domain=domain, key=key)
    if domain is None and getattr(provider, "peer_info", None):
        props = provider.peer_info.get("Properties", {})
        values = {
            "UniqueDeviceID": props.get("UniqueDeviceID", ""),
            "ProductType": props.get("ProductType", ""),
            "ProductVersion": props.get("OSVersion", ""),
            "BuildVersion": props.get("BuildVersion", ""),
            "DeviceClass": props.get("DeviceClass", ""),
            "DeviceName": props.get("DeviceName", ""),
        }
        return values.get(key) if key else values
    raise DeviceError(_("The device does not answer this question."))


async def device_info(lockdown, transport: str = USB) -> DeviceInfo:
    v = await get_value(lockdown)
    dev_mode = False
    try:
        dev_mode = bool(await lockdown.get_developer_mode_status())
    except Exception:
        # Older systems don't know the switch - it doesn't exist there, and
        # that is not an error.
        pass
    product_type = v.get("ProductType", "?")
    udid = v.get("UniqueDeviceID", "")
    known = registry.get(udid) if udid else None
    return DeviceInfo(
        udid=udid,
        name=v.get("DeviceName") or (known.name if known else "") or "?",
        product_type=product_type,
        ios_version=v.get("ProductVersion", "?"),
        build=v.get("BuildVersion", "?"),
        developer_mode=dev_mode,
        platform=registry.platform_for(product_type, v.get("DeviceClass", "")),
        transport=transport,
    )


@dataclass(frozen=True)
class Battery:
    level: int          # percent
    charging: bool


async def battery(lockdown) -> Battery | None:
    """Battery level - ``None`` if the device doesn't reveal it (or has none,
    like an Apple TV)."""
    try:
        v = await get_value(lockdown, domain="com.apple.mobile.battery")
        return Battery(level=int(v["BatteryCurrentCapacity"]),
                       charging=bool(v.get("BatteryIsCharging")))
    except Exception:
        return None


class ServiceProvider:
    """Holds lockdown and - when needed - the RSD tunnel.

    Usage::

        async with ServiceProvider(udid) as sp:
            info = await device_info(sp.lockdown, sp.transport)
    """

    def __init__(self, udid: str | None = None, *, ref: DeviceRef | None = None) -> None:
        self.udid = udid
        self.ref = ref
        self.transport = ref.transport if ref else USB
        self.lockdown = None
        self._tunnel = None
        self._rsd = None

    @property
    def is_network(self) -> bool:
        return self.transport in discovery.NETWORK

    async def __aenter__(self) -> "ServiceProvider":
        self.ref = self.ref or await resolve(self.udid)
        self.transport = self.ref.transport
        if self.transport == WIFI:
            try:
                self.lockdown = await connect(ref=self.ref)
            except DeviceNotFound as exc:
                # Lockdown over Wi-Fi does not answer (the iPhone dozes), but
                # its RemotePairing side may: that tunnel carries every
                # service lockdown would.
                known = registry.get(self.ref.udid)
                remote = (await _remote_ref(self.ref.udid)
                          if known is not None and known.remote_identifier else None)
                if remote is None:
                    raise DeviceNotFound(_(
                        "The iPhone is known in the network but does not answer "
                        "right now. Unlock it (or wake it up) and try again - "
                        "or connect it via USB.")) from exc
                log.info("Lockdown over Wi-Fi does not answer - using RemotePairing")
                self.ref = remote
                self.transport = REMOTE
        if self.transport == REMOTE:
            # Nothing but the tunnel - the RSD stands in for lockdown.
            self.lockdown = await self.rsd()
        elif self.lockdown is None:
            self.lockdown = await connect(ref=self.ref)
        if self.transport != REMOTE:
            _learn(self.lockdown, self.transport)
        self.udid = getattr(self.lockdown, "udid", None) or self.ref.udid
        return self

    async def __aexit__(self, *exc) -> None:
        if self._tunnel is not None:
            try:
                await self._tunnel.close()
            except Exception:
                pass
        if self.lockdown is not None and self.lockdown is not self._rsd:
            try:
                await self.lockdown.close()
            except Exception:
                pass

    async def rsd(self):
        """Sets up the userspace RSD tunnel (without root) and caches it.

        Over the network there can be more than one way; they are tried in
        order and the first that stands is kept."""
        if self._rsd is not None:
            return self._rsd
        from . import tunnel

        errors: list[str] = []
        # A dozing device answers in the network one moment and not the next
        # (seen with iPhones: timeouts, dropped connections) - so a few quick
        # retries there. The cable either works or it doesn't.
        attempts = NETWORK_TUNNEL_ATTEMPTS if self.is_network else 1
        for candidate in await self._tunnel_candidates(tunnel):
            for attempt in range(attempts):
                try:
                    self._rsd = await candidate.open()
                    self._tunnel = candidate
                    return self._rsd
                except DeviceError:
                    raise
                except Exception as exc:
                    # Only the log file - the next try may well work.
                    log.debug("RSD tunnel attempt %d failed: %r", attempt + 1, exc)
                    errors.append(_error_text(exc))
                    try:
                        await candidate.close()
                    except Exception:
                        pass
                    if attempt + 1 < attempts:
                        await asyncio.sleep(NETWORK_RETRY_PAUSE)
        error = "; ".join(dict.fromkeys(errors))
        if self.is_network:
            raise DeviceError(_(
                "RSD tunnel over the network could not be established: "
                "{error}\nThe device has to be awake and in the same "
                "network.", error=error))
        raise DeviceError(_(
            "RSD tunnel could not be established: {error}\nFrom iOS 17 "
            "on, installing apps needs this tunnel. Often helps: unlock "
            "the iPhone, re-plug the cable.", error=error))

    async def _tunnel_candidates(self, tunnel) -> list:
        ref = self.ref
        if ref is None or ref.transport == USB:
            return [tunnel.usb_tunnel(self.udid)]
        if ref.transport == REMOTE:
            return [tunnel.provider_tunnel(tunnel.remote_pairing(ref.identifier, ref.host, ref.port))]
        # Wi-Fi or usbmuxd's network. RemotePairing first: it is the way Xcode
        # takes over Wi-Fi. The CoreDevice proxy behind lockdown opens over
        # Wi-Fi too, but iOS (seen on 27) drops the connection as soon as the
        # tunnel is requested - it only serves the cable. Kept as a fallback.
        out = []
        known = registry.get(ref.udid)
        if known is not None and known.remote_identifier:
            remote = await _remote_ref(ref.udid)
            if remote is not None:
                out.append(tunnel.provider_tunnel(
                    tunnel.remote_pairing(remote.identifier, remote.host, remote.port)))
        if _version_at_least(getattr(self.lockdown, "product_version", ""), (17, 4)):
            out.append(tunnel.provider_tunnel(tunnel.core_device_proxy(self.lockdown)))
        if not out:
            raise DeviceError(_(
                "Developer services over Wi-Fi need a developer tunnel, and "
                "this iPhone has none yet. Connect it via USB once and switch "
                "on Wi-Fi for it again - or use the cable for this."))
        return out


def _error_text(exc: BaseException) -> str:
    """Never an empty message - pymobiledevice3 raises several errors
    without one (ConnectionTerminatedError())."""
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


async def _remote_ref(udid: str) -> DeviceRef | None:
    """The device's RemotePairing advert - from the background search, or,
    if that has not seen it (yet: right after the start), searched for now."""
    def pick(refs):
        return next((r for r in refs if r.udid == udid and r.transport == REMOTE), None)

    scanner = discovery.SCANNER
    hit = pick(scanner.refs()) if scanner is not None else None
    if hit is not None:
        return hit
    found = await discovery.NetworkScanner().scan()
    if scanner is not None:
        scanner._record(found)
    return pick(found)


def _version_at_least(version: str, wanted: tuple[int, ...]) -> bool:
    parts = []
    for p in str(version).split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) >= wanted if parts else False


def _learn(lockdown, transport: str) -> None:
    """Keeps name, model and version of a known device current - a network
    device should show its name without being asked first."""
    values = getattr(lockdown, "all_values", None) or {}
    udid = values.get("UniqueDeviceID")
    if not udid:
        return
    known = registry.get(udid)
    fresh = {
        "name": values.get("DeviceName", ""),
        "product_type": values.get("ProductType", ""),
        "os_version": values.get("ProductVersion", ""),
        "wifi_mac": (values.get("WiFiAddress") or "").lower(),
        "platform": registry.platform_for(values.get("ProductType", ""),
                                          values.get("DeviceClass", "")),
    }
    if known is None:
        # Remembered from the cable on: the device list can name it later,
        # and Wi-Fi can be switched on for it.
        if transport == USB:
            registry.remember(udid, **fresh)
        return
    if any(v and getattr(known, k) != v for k, v in fresh.items()):
        registry.remember(udid, **fresh)
