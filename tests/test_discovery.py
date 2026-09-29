"""Which device is where - cable, usbmuxd's network, Wi-Fi, RemotePairing."""

from __future__ import annotations

import pytest

from modstaller.device import discovery, registry
from modstaller.device.discovery import REMOTE, USB, USBMUX_NET, WIFI, DeviceRef


def test_the_best_way_wins_and_order_is_kept():
    refs = discovery.merge(
        [DeviceRef("B", USB)],
        [DeviceRef("A", WIFI, host="10.0.0.2"), DeviceRef("B", WIFI, host="10.0.0.3"),
         DeviceRef("A", REMOTE, host="10.0.0.2", port=5)])
    assert [(r.udid, r.transport) for r in refs] == [("B", USB), ("A", WIFI)]


async def test_usbmux_tells_cable_from_network(monkeypatch):
    from pymobiledevice3.usbmux import MuxDevice

    async def listing():
        return [MuxDevice(1, "U1", "USB"), MuxDevice(2, "N1", "Network")]
    monkeypatch.setattr("pymobiledevice3.usbmux.list_devices", listing)
    refs = await discovery.usbmux_refs()
    assert [(r.udid, r.transport) for r in refs] == [("U1", USB), ("N1", USBMUX_NET)]


def test_seen_devices_expire():
    scanner = discovery.NetworkScanner(ttl=45)
    scanner._record([DeviceRef("A", WIFI, host="10.0.0.2")], now=100.0)
    assert [r.udid for r in scanner.refs(now=140.0)] == ["A"]
    assert scanner.refs(now=146.0) == []


def test_a_new_address_is_remembered():
    registry.remember("A", name="iPhone", wifi_enabled=True)
    scanner = discovery.NetworkScanner()
    scanner._record([DeviceRef("A", WIFI, host="10.0.0.2")])
    assert registry.get("A").last_host == "10.0.0.2"


class _Addr:
    def __init__(self, ip):
        self.ip = ip

    @property
    def full_ip(self):
        return self.ip


class _Answer:
    def __init__(self, instance, ips, port=0, properties=None):
        self.instance = instance
        self.addresses = [_Addr(i) for i in ips]
        self.port = port
        self.properties = properties or {}


async def test_mobdev2_adverts_are_matched_by_wifi_mac(monkeypatch):
    registry.remember("A", name="iPhone", wifi_enabled=True, wifi_mac="aa:bb:cc:dd:ee:ff")
    registry.remember("B", name="Other", wifi_enabled=False, wifi_mac="11:22:33:44:55:66")

    async def browse(timeout):
        return [_Answer("aa:bb:cc:dd:ee:ff@fe80::1._apple-mobdev2._tcp.local.", ["fe80::1", "10.0.0.2"]),
                _Answer("11:22:33:44:55:66@fe80::2._apple-mobdev2._tcp.local.", ["10.0.0.3"])]
    monkeypatch.setattr("pymobiledevice3.bonjour.browse_mobdev2", browse)

    async def no_identify(self, answer, host):
        return None
    monkeypatch.setattr(discovery.NetworkScanner, "_identify", no_identify)

    found = await discovery.NetworkScanner().scan()
    # IPv4 first; B has Wi-Fi off in ModStaller and is not offered.
    assert found == [DeviceRef("A", WIFI, host="10.0.0.2")]


async def test_nothing_is_searched_without_known_network_devices(monkeypatch):
    async def browse(timeout):
        raise AssertionError("must not browse")
    monkeypatch.setattr("pymobiledevice3.bonjour.browse_mobdev2", browse)
    monkeypatch.setattr("pymobiledevice3.bonjour.browse_remotepairing", browse)
    assert await discovery.NetworkScanner().scan() == []


async def test_attached_uses_the_background_search(monkeypatch):
    async def none(**kw):
        return []
    monkeypatch.setattr(discovery, "usbmux_refs", none)
    scanner = discovery.NetworkScanner()
    scanner._record([DeviceRef("A", WIFI, host="10.0.0.2")])
    monkeypatch.setattr(discovery, "SCANNER", scanner)
    assert [r.udid for r in await discovery.attached()] == ["A"]


async def test_a_missing_usb_service_only_matters_without_network_devices(monkeypatch):
    from modstaller.errors import UsbServiceUnavailable

    async def missing(**kw):
        raise UsbServiceUnavailable("service missing")
    monkeypatch.setattr(discovery, "usbmux_refs", missing)
    with pytest.raises(UsbServiceUnavailable):
        await discovery.attached()
    scanner = discovery.NetworkScanner()
    scanner._record([DeviceRef("A", WIFI, host="10.0.0.2")])
    monkeypatch.setattr(discovery, "SCANNER", scanner)
    assert [r.udid for r in await discovery.attached()] == ["A"]
