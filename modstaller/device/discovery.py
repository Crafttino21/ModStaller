"""Which devices are there, and over which way they can be reached.

Two sources:

* **usbmuxd** - devices on the cable, and on Windows (Apple's device
  service with Wi-Fi sync on) or with netmuxd also devices in the network.
  It tells which one is which (``connection_type``).
* **Bonjour** - devices in the same network that ModStaller knows from
  :mod:`.registry`: iPhones advertise ``_apple-mobdev2._tcp`` once Wi-Fi
  connections are on, paired Apple TVs (and iOS 17+) ``_remotepairing._tcp``.

A browse takes seconds; the interface asks for the status every three. So
the network is searched in the background (:class:`NetworkScanner`) and the
status only reads what was last seen.

One device can show up on several ways at once. The best one wins - the
cable before the network, lockdown before a pure RemotePairing tunnel.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass

from .. import config
from ..errors import UsbServiceUnavailable
from ..i18n import _
from . import registry

log = logging.getLogger(__name__)

USB = "usb"
#: A network device handed out by usbmuxd (Windows with Wi-Fi sync, netmuxd).
USBMUX_NET = "usbmux-net"
#: Lockdown over TCP with the pair record from the cable (``_apple-mobdev2``).
WIFI = "wifi"
#: Only a RemotePairing tunnel - an Apple TV, or an iPhone as a fallback.
REMOTE = "remote"

PRIORITY = {USB: 0, USBMUX_NET: 1, WIFI: 2, REMOTE: 3}
NETWORK = {USBMUX_NET, WIFI, REMOTE}

#: How long one Bonjour browse listens.
BROWSE_TIMEOUT = 3.0
#: Pause between two searches.
SCAN_INTERVAL = 15.0
#: A device not seen for this long counts as gone.
SEEN_TTL = 45.0


@dataclass(frozen=True)
class DeviceRef:
    udid: str
    transport: str
    host: str = ""
    port: int = 0
    #: RemotePairing record identifier (transport ``remote``).
    identifier: str = ""

    @property
    def is_network(self) -> bool:
        return self.transport in NETWORK


def usb_service_hint() -> str:
    """What to do when the Apple device service is missing (Windows)."""
    return _("ModStaller can set it up by itself (“modstaller usb-setup” or "
             "the button on the overview) - or install the “Apple Devices” "
             "app from the Microsoft Store.")


async def usbmux_refs(*, posix: bool | None = None) -> list[DeviceRef]:
    """What usbmuxd lists - cable and, where it can, network.

    Raises :class:`UsbServiceUnavailable` on Windows when the Apple device
    service does not answer - without it no iPhone is ever visible, even
    though Explorer shows one.
    """
    from pymobiledevice3.exceptions import ConnectionFailedToUsbmuxdError
    from pymobiledevice3.usbmux import list_devices as _ls

    if posix is None:
        posix = config.POSIX
    try:
        devices = await _ls()
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
    return [DeviceRef(d.serial, USBMUX_NET if getattr(d, "is_network", False) else USB)
            for d in devices]


def merge(*groups: list[DeviceRef]) -> list[DeviceRef]:
    """One entry per device - the best way to reach it. Order: as first seen."""
    best: dict[str, DeviceRef] = {}
    for group in groups:
        for ref in group:
            have = best.get(ref.udid)
            if have is None or PRIORITY[ref.transport] < PRIORITY[have.transport]:
                best[ref.udid] = ref
    order = list(dict.fromkeys(r.udid for g in groups for r in g))
    return [best[u] for u in order]


def _pick_address(answer) -> str:
    """IPv4 first - link-local IPv6 needs the interface and trips up more
    network setups than it helps."""
    addresses = list(getattr(answer, "addresses", []) or [])
    for a in addresses:
        if ":" not in a.ip:
            return a.full_ip
    return addresses[0].full_ip if addresses else ""


class NetworkScanner:
    """Searches the network for known devices in the background."""

    def __init__(self, *, interval: float = SCAN_INTERVAL, ttl: float = SEEN_TTL,
                 browse_timeout: float = BROWSE_TIMEOUT) -> None:
        self.interval = interval
        self.ttl = ttl
        self.browse_timeout = browse_timeout
        self._seen: dict[str, tuple[DeviceRef, float]] = {}
        self._lock = threading.Lock()
        #: mobdev2 instance name -> udid, for devices with a private Wi-Fi
        #: address (the advert then does not carry the real MAC).
        self._instances: dict[str, str] = {}
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None

    # -- Lifecycle --

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="network-scan", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def poke(self) -> None:
        """Search now instead of at the next interval - e.g. right after Wi-Fi
        was switched on for a device."""
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                asyncio.run(self.scan())
            except Exception:
                log.warning("Network search failed", exc_info=True)
            self._wake.wait(self.interval)
            self._wake.clear()

    # -- Results --

    def refs(self, now: float | None = None) -> list[DeviceRef]:
        now = time.monotonic() if now is None else now
        with self._lock:
            return [ref for ref, at in self._seen.values() if now - at <= self.ttl]

    def _record(self, refs: list[DeviceRef], now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            moved = []
            for ref in refs:
                key = f"{ref.transport}:{ref.udid}"
                old = self._seen.get(key)
                if old is None or old[0].host != ref.host:
                    moved.append(ref)
                self._seen[key] = (ref, now)
        # Only when the address changed - not a disk write every 15 seconds.
        for ref in moved:
            registry.remember(ref.udid, last_host=ref.host)

    def forget(self, udid: str) -> None:
        with self._lock:
            for key in [k for k, (r, _) in self._seen.items() if r.udid == udid]:
                del self._seen[key]

    # -- Searching --

    async def scan(self) -> list[DeviceRef]:
        known = registry.all_devices()
        found: list[DeviceRef] = []
        if any(d.wifi_enabled for d in known):
            found += await self._scan_mobdev2(known)
        if any(d.remote_identifier for d in known):
            found += await self._scan_remotepairing(known)
        self._record(found)
        return found

    async def _scan_mobdev2(self, known: list[registry.KnownDevice]) -> list[DeviceRef]:
        from pymobiledevice3.bonjour import browse_mobdev2

        wifi = [d for d in known if d.wifi_enabled]
        by_mac = {d.wifi_mac: d for d in wifi if d.wifi_mac}
        out = []
        for answer in await browse_mobdev2(timeout=self.browse_timeout):
            host = _pick_address(answer)
            if not host:
                continue
            mac = answer.instance.split("@", 1)[0].lower() if "@" in answer.instance else ""
            dev = by_mac.get(mac)
            udid = dev.udid if dev else self._instances.get(answer.instance)
            if udid is None:
                udid = await self._identify(answer, host)
                if udid is None:
                    continue
                self._instances[answer.instance] = udid
            out.append(DeviceRef(udid, WIFI, host=host))
        return out

    async def _identify(self, answer, host: str) -> str | None:
        """A device with a private Wi-Fi address: ask it who it is, offering
        only the pair records of the hosts it says it is paired with."""
        from pymobiledevice3.lockdown import (
            _mobdev2_pair_record_candidates, create_using_tcp,
        )

        records = registry.all_pair_records()
        candidates = _mobdev2_pair_record_candidates(answer, list(records.values()))
        for record in candidates:
            try:
                lockdown = await create_using_tcp(hostname=host, autopair=False, pair_record=record,
                                                  label="ModStaller")
            except Exception:
                continue
            try:
                if lockdown.paired and lockdown.udid in records:
                    return lockdown.udid
            finally:
                await lockdown.close()
        return None

    async def _scan_remotepairing(self, known: list[registry.KnownDevice]) -> list[DeviceRef]:
        from pymobiledevice3.bonjour import browse_remotepairing
        from pymobiledevice3.pair_records import iter_remote_pair_records_by_identifier
        from pymobiledevice3.remote.tunnel_service import _match_remote_pair_record

        by_identifier = {d.remote_identifier: d for d in known if d.remote_identifier}
        alt_irks = {}
        for identifier, _path, record in iter_remote_pair_records_by_identifier():
            if identifier in by_identifier and record.get("peer_alt_irk") is not None:
                alt_irks[identifier] = record["peer_alt_irk"]
        if not alt_irks:
            return []
        out = []
        for answer in await browse_remotepairing(timeout=self.browse_timeout):
            identifier = _match_remote_pair_record(answer, alt_irks)
            host = _pick_address(answer)
            if identifier is None or not host:
                continue
            dev = by_identifier[identifier]
            out.append(DeviceRef(dev.udid, REMOTE, host=host, port=answer.port, identifier=identifier))
        return out


#: Set by the server - there the search runs in the background. Without it
#: (the CLI) :func:`attached` searches once, on demand.
SCANNER: NetworkScanner | None = None


async def attached(*, posix: bool | None = None, search: bool = True) -> list[DeviceRef]:
    """Every reachable device, one entry each, cable first.

    ``search=False``: only what is known without waiting (usbmux and the
    background search) - for the status, which must never block.
    """
    usb_error: UsbServiceUnavailable | None = None
    try:
        local = await usbmux_refs(posix=posix)
    except UsbServiceUnavailable as exc:
        local, usb_error = [], exc
    if SCANNER is not None:
        network = SCANNER.refs()
    elif search and any(d.wifi_enabled or d.remote_identifier for d in registry.all_devices()):
        network = await NetworkScanner().scan()
    else:
        network = []
    refs = merge(local, network)
    if usb_error is not None and not refs:
        raise usb_error
    return refs
