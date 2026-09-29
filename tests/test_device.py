"""Device layer against a mocked lockdown.

pymobiledevice3 is asynchronous throughout. A forgotten ``await`` doesn't
show up on import but only on the device - with a message
("'coroutine' object has no attribute ...", "was never awaited") that leads
away from the actual spot. These tests walk the paths without an iPhone and
fail exactly when an await is missing.
"""

from __future__ import annotations

import pytest

from modstaller.device.connection import DeviceInfo, ServiceProvider, device_info

VALUES = {
    "UniqueDeviceID": "00008140-00067D110CE8401C",
    "DeviceName": "iPhone von Santino",
    "ProductType": "iPhone17,2",
    "ProductVersion": "27.0",
    "BuildVersion": "24A437",
}


class FakeLockdown:
    """Mock with the same asynchronous signatures as the original."""

    udid = VALUES["UniqueDeviceID"]

    def __init__(self, dev_mode: bool = True, dev_mode_raises: bool = False):
        self._dev_mode = dev_mode
        self._raises = dev_mode_raises
        self.closed = False

    async def get_value(self, domain=None, key=None):
        return VALUES

    async def get_developer_mode_status(self) -> bool:
        if self._raises:
            raise RuntimeError("unknown domain")
        return self._dev_mode

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_device_info_reads_values():
    info = await device_info(FakeLockdown())
    assert isinstance(info, DeviceInfo)
    assert info.udid == VALUES["UniqueDeviceID"]
    assert info.ios_version == "27.0"
    assert info.build == "24A437"
    assert info.product_type == "iPhone17,2"
    assert info.developer_mode is True


@pytest.mark.asyncio
async def test_device_info_survives_missing_developer_mode_switch():
    """Older systems don't know the switch - that is not an error."""
    info = await device_info(FakeLockdown(dev_mode_raises=True))
    assert info.developer_mode is False


@pytest.mark.asyncio
async def test_device_info_renders_warning_when_developer_mode_off():
    text = str(await device_info(FakeLockdown(dev_mode=False)))
    assert "OFF" in text


@pytest.mark.asyncio
async def test_service_provider_closes_lockdown(monkeypatch):
    fake = FakeLockdown()

    async def fake_connect(udid=None, timeout=0.0, ref=None):
        return fake

    async def fake_resolve(udid=None):
        from modstaller.device.discovery import USB, DeviceRef
        return DeviceRef(VALUES["UniqueDeviceID"], USB)

    monkeypatch.setattr("modstaller.device.connection.connect", fake_connect)
    monkeypatch.setattr("modstaller.device.connection.resolve", fake_resolve)
    async with ServiceProvider() as sp:
        assert sp.udid == VALUES["UniqueDeviceID"]
    assert fake.closed, "lockdown must be closed"


@pytest.mark.asyncio
async def test_list_devices_is_empty_without_usbmuxd():
    """usbmuxd is socket-activated: without an iPhone it isn't running.
    That must not raise, but simply yield an empty list.

    Windows is different: there a missing service is named instead (the CI
    runner has no Apple Devices) - see the test below."""
    from modstaller import config
    from modstaller.device.connection import list_devices
    from modstaller.errors import UsbServiceUnavailable
    try:
        assert isinstance(await list_devices(), list)
    except UsbServiceUnavailable:
        assert not config.POSIX, "only Windows names a missing service"


@pytest.mark.asyncio
@pytest.mark.parametrize("posix", [True, False])
async def test_a_missing_usb_service_is_named_on_windows_only(monkeypatch, posix):
    """Windows shows the iPhone in Explorer even without the Apple device
    service - "no iPhone" would be a lie there. On Linux a missing usbmuxd
    socket just means nothing is plugged in."""
    from pymobiledevice3.exceptions import ConnectionFailedToUsbmuxdError

    from modstaller.device.connection import list_devices
    from modstaller.errors import UsbServiceUnavailable

    async def refused():
        raise ConnectionFailedToUsbmuxdError()
    monkeypatch.setattr("pymobiledevice3.usbmux.list_devices", refused)

    if posix:
        assert await list_devices(posix=True) == []
    else:
        with pytest.raises(UsbServiceUnavailable, match="Apple Devices"):
            await list_devices(posix=False)


@pytest.mark.asyncio
async def test_unexpected_listing_errors_are_logged_not_swallowed(monkeypatch, caplog):
    from modstaller.device.connection import list_devices

    async def broken():
        raise RuntimeError("boom")
    monkeypatch.setattr("pymobiledevice3.usbmux.list_devices", broken)

    assert await list_devices(posix=False) == []
    assert "boom" in caplog.text


class _FakeTunnel:
    def __init__(self, name, log, fails=False):
        self.name, self.log, self.fails = name, log, fails

    async def open(self):
        self.log.append(("open", self.name))
        if self.fails:
            from pymobiledevice3.exceptions import ConnectionTerminatedError
            raise ConnectionTerminatedError()
        return f"rsd-{self.name}"

    async def close(self):
        self.log.append(("close", self.name))


class _FakeTunnelModule:
    """Stands in for device.tunnel - records which way was built."""

    def __init__(self, proxy_fails=False, remote_fails=False):
        self.log = []
        self.proxy_fails, self.remote_fails = proxy_fails, remote_fails

    def usb_tunnel(self, udid):
        return _FakeTunnel("usb", self.log)

    def remote_pairing(self, identifier, host, port):
        return ("remote", identifier, host, port)

    def core_device_proxy(self, lockdown):
        return ("proxy",)

    def provider_tunnel(self, factory):
        name = factory[0]
        fails = self.remote_fails if name == "remote" else self.proxy_fails
        return _FakeTunnel(name, self.log, fails)


class _WifiLockdown:
    product_version = "27.0.1"


def _wifi_sp(monkeypatch, *, remote_seen=True):
    from modstaller.device import discovery, registry
    from modstaller.device.discovery import REMOTE, WIFI, DeviceRef

    registry.remember("U1", name="iPhone", wifi_enabled=True, remote_identifier="U1")
    scanner = discovery.NetworkScanner()
    if remote_seen:
        scanner._record([DeviceRef("U1", REMOTE, host="10.0.0.2", port=49152, identifier="U1")])
    monkeypatch.setattr(discovery, "SCANNER", scanner)
    sp = ServiceProvider(ref=DeviceRef("U1", WIFI, host="10.0.0.2"))
    sp.udid = "U1"
    sp.transport = WIFI
    sp.lockdown = _WifiLockdown()
    return sp


@pytest.mark.asyncio
async def test_over_wifi_remotepairing_comes_first(monkeypatch):
    """iOS drops the CoreDevice proxy tunnel over Wi-Fi (seen on 27) - the
    RemotePairing tunnel is the way that works there."""
    fake = _FakeTunnelModule()
    monkeypatch.setitem(__import__("sys").modules, "modstaller.device.tunnel", fake)
    monkeypatch.setattr("modstaller.device.tunnel", fake, raising=False)
    sp = _wifi_sp(monkeypatch)
    assert await sp.rsd() == "rsd-remote"
    assert fake.log == [("open", "remote")]


@pytest.mark.asyncio
async def test_a_failing_way_falls_back_and_names_the_error(monkeypatch):
    from modstaller.errors import DeviceError

    fake = _FakeTunnelModule(remote_fails=True)
    monkeypatch.setitem(__import__("sys").modules, "modstaller.device.tunnel", fake)
    monkeypatch.setattr("modstaller.device.tunnel", fake, raising=False)
    monkeypatch.setattr("modstaller.device.connection.NETWORK_RETRY_PAUSE", 0)
    sp = _wifi_sp(monkeypatch)
    assert await sp.rsd() == "rsd-proxy"
    # A dozing device gets a few tries per way before the next way.
    assert fake.log == [("open", "remote"), ("close", "remote")] * 3 + [("open", "proxy")]

    fake2 = _FakeTunnelModule(remote_fails=True, proxy_fails=True)
    monkeypatch.setitem(__import__("sys").modules, "modstaller.device.tunnel", fake2)
    monkeypatch.setattr("modstaller.device.tunnel", fake2, raising=False)
    sp2 = _wifi_sp(monkeypatch)
    with pytest.raises(DeviceError, match="ConnectionTerminatedError"):
        await sp2.rsd()


@pytest.mark.asyncio
async def test_a_dozing_iphone_is_reached_over_remotepairing(monkeypatch):
    """Lockdown over Wi-Fi does not answer while the iPhone dozes - its
    RemotePairing side often still does. No "no device found" then."""
    from modstaller.device import discovery, registry
    from modstaller.device.discovery import REMOTE, WIFI, DeviceRef
    from modstaller.errors import DeviceNotFound

    registry.remember("U1", name="iPhone", wifi_enabled=True, remote_identifier="U1")
    scanner = discovery.NetworkScanner()
    scanner._record([DeviceRef("U1", REMOTE, host="10.0.0.2", port=49152, identifier="U1")])
    monkeypatch.setattr(discovery, "SCANNER", scanner)

    async def silent(udid=None, timeout=0.0, ref=None):
        raise DeviceNotFound("no answer")
    monkeypatch.setattr("modstaller.device.connection.connect", silent)
    fake = _FakeTunnelModule()
    monkeypatch.setitem(__import__("sys").modules, "modstaller.device.tunnel", fake)
    monkeypatch.setattr("modstaller.device.tunnel", fake, raising=False)

    async with ServiceProvider(ref=DeviceRef("U1", WIFI, host="10.0.0.2")) as sp:
        assert sp.transport == REMOTE
        assert sp.lockdown == "rsd-remote"


@pytest.mark.asyncio
async def test_without_remotepairing_the_message_says_it_does_not_answer(monkeypatch):
    from modstaller.device import registry
    from modstaller.device.discovery import WIFI, DeviceRef
    from modstaller.errors import DeviceNotFound

    registry.remember("U1", name="iPhone", wifi_enabled=True)

    async def silent(udid=None, timeout=0.0, ref=None):
        raise DeviceNotFound("no answer")
    monkeypatch.setattr("modstaller.device.connection.connect", silent)
    with pytest.raises(DeviceNotFound, match="does not answer"):
        async with ServiceProvider(ref=DeviceRef("U1", WIFI, host="10.0.0.2")):
            pass


@pytest.mark.asyncio
async def test_a_device_the_search_just_missed_is_looked_for_once_more(monkeypatch):
    from modstaller.device import connection, discovery, registry
    from modstaller.device.discovery import REMOTE, DeviceRef

    registry.remember("U1", name="iPhone", wifi_enabled=True, remote_identifier="U1")

    async def nothing(**kw):
        return []
    monkeypatch.setattr(discovery, "usbmux_refs", nothing)
    monkeypatch.setattr(discovery, "SCANNER", discovery.NetworkScanner())
    searched = []

    async def scan(self):
        searched.append(True)
        return [DeviceRef("U1", REMOTE, host="10.0.0.2", port=49152, identifier="U1")]
    monkeypatch.setattr(discovery.NetworkScanner, "scan", scan)

    ref = await connection.resolve("U1")
    assert ref.transport == REMOTE and searched == [True]
    # ... and the background search now knows it too.
    assert discovery.SCANNER.refs()


@pytest.mark.asyncio
async def test_a_flaky_network_way_is_retried(monkeypatch):
    fake = _FakeTunnelModule()
    tries = []
    orig = _FakeTunnel.open

    async def flaky(self):
        tries.append(self.name)
        if len(tries) < 2:
            raise TimeoutError()
        return await orig(self)
    monkeypatch.setattr(_FakeTunnel, "open", flaky)
    monkeypatch.setattr("modstaller.device.connection.NETWORK_RETRY_PAUSE", 0)
    monkeypatch.setitem(__import__("sys").modules, "modstaller.device.tunnel", fake)
    monkeypatch.setattr("modstaller.device.tunnel", fake, raising=False)
    sp = _wifi_sp(monkeypatch)
    assert await sp.rsd() == "rsd-remote"
    assert tries == ["remote", "remote"]
