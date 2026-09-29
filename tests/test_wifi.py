"""Wi-Fi for an iPhone: switched on over the cable, used without it."""

from __future__ import annotations

import pytest

from modstaller.device import registry, wifi
from modstaller.errors import DeviceError

VALUES = {"UniqueDeviceID": "U1", "DeviceName": "iPhone of S", "ProductType": "iPhone17,2",
          "ProductVersion": "16.7", "WiFiAddress": "AA:BB:CC:DD:EE:FF"}


class FakeLockdown:
    def __init__(self, values=VALUES):
        self.all_values = dict(values)
        self.pair_record = {"HostID": "H", "WiFiMACAddress": "aa:bb:cc:dd:ee:ff"}
        self.wifi = None

    async def set_enable_wifi_connections(self, value):
        self.wifi = value

    async def get_value(self, domain=None, key=None):
        return self.all_values


class FakeSP:
    def __init__(self, transport="usb", lockdown=None):
        self.transport = transport
        self.lockdown = lockdown or FakeLockdown()
        self.udid = self.lockdown.all_values["UniqueDeviceID"]
        self._rsd = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass


@pytest.fixture
def sp(monkeypatch):
    holder = {"sp": FakeSP()}
    monkeypatch.setattr(wifi, "ServiceProvider", lambda udid=None: holder["sp"])
    return holder


async def test_switching_on_keeps_the_pairing_and_the_mac(sp):
    out = await wifi.enable()
    assert sp["sp"].lockdown.wifi is True
    dev = registry.get("U1")
    assert dev.wifi_enabled and dev.wifi_mac == "aa:bb:cc:dd:ee:ff"
    assert dev.name == "iPhone of S"
    assert registry.load_pair_record("U1")["HostID"] == "H"
    # iOS 16: no RemotePairing, and no tunnel over Wi-Fi.
    assert dev.remote_identifier == ""
    assert out == {"udid": "U1", "tunnel": False}


async def test_ios_17_also_pairs_remotepairing_over_the_cable(sp, monkeypatch):
    sp["sp"] = FakeSP(lockdown=FakeLockdown({**VALUES, "ProductVersion": "17.2"}))
    called = []

    async def pair_remote(lockdown, on_step):
        called.append(lockdown)
        return True
    monkeypatch.setattr(wifi, "_pair_remote", pair_remote)
    out = await wifi.enable()
    assert called and registry.get("U1").remote_identifier == "U1"
    assert out["tunnel"] is True


async def test_a_failed_remotepairing_is_not_fatal(sp, monkeypatch):
    sp["sp"] = FakeSP(lockdown=FakeLockdown({**VALUES, "ProductVersion": "18.1"}))

    async def broken(lockdown, on_step):
        raise RuntimeError("no service")
    monkeypatch.setattr(wifi, "_pair_remote", broken)
    steps = []
    await wifi.enable(on_step=steps.append)
    assert registry.get("U1").wifi_enabled
    assert any("no service" in s for s in steps)


async def test_switching_on_needs_the_cable(sp):
    sp["sp"] = FakeSP(transport="wifi")
    with pytest.raises(DeviceError, match="USB"):
        await wifi.enable()


async def test_an_apple_tv_is_not_switched_on_this_way(sp):
    sp["sp"] = FakeSP(lockdown=FakeLockdown({**VALUES, "ProductType": "AppleTV14,1"}))
    with pytest.raises(DeviceError, match="PIN"):
        await wifi.enable()


async def test_switching_off_forgets_the_pairing(sp):
    await wifi.enable()
    await wifi.disable("U1")
    dev = registry.get("U1")
    assert not dev.wifi_enabled
    assert registry.load_pair_record("U1") is None
    assert sp["sp"].lockdown.wifi is False


async def test_switching_off_works_without_the_device(sp, monkeypatch):
    await wifi.enable()

    class Gone:
        async def __aenter__(self):
            from modstaller.errors import DeviceNotFound
            raise DeviceNotFound("gone")

        async def __aexit__(self, *exc):
            pass
    monkeypatch.setattr(wifi, "ServiceProvider", lambda udid=None: Gone())
    out = await wifi.disable("U1")
    assert out["deviceUpdated"] is False
    assert not registry.get("U1").wifi_enabled
