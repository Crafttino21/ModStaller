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

    async def fake_connect(udid=None, timeout=0.0):
        return fake

    monkeypatch.setattr("modstaller.device.connection.connect", fake_connect)
    async with ServiceProvider() as sp:
        assert sp.udid == VALUES["UniqueDeviceID"]
    assert fake.closed, "lockdown must be closed"


@pytest.mark.asyncio
async def test_list_devices_is_empty_without_usbmuxd():
    """usbmuxd is socket-activated: without an iPhone it isn't running.
    That must not raise, but simply yield an empty list."""
    from modstaller.device.connection import list_devices
    assert isinstance(await list_devices(), list)
