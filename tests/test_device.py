"""Geraete-Schicht gegen ein nachgebildetes lockdown.

pymobiledevice3 ist durchgehend asynchron. Ein vergessenes ``await`` faellt
nicht beim Import auf, sondern erst am Geraet - mit einer Meldung
("'coroutine' object has no attribute ...", "was never awaited"), die vom
eigentlichen Ort wegfuehrt. Diese Tests laufen die Pfade ohne iPhone ab und
scheitern genau dann, wenn ein await fehlt.
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
    """Nachbildung mit denselben asynchronen Signaturen wie das Original."""

    udid = VALUES["UniqueDeviceID"]

    def __init__(self, dev_mode: bool = True, dev_mode_raises: bool = False):
        self._dev_mode = dev_mode
        self._raises = dev_mode_raises
        self.closed = False

    async def get_value(self, domain=None, key=None):
        return VALUES

    async def get_developer_mode_status(self) -> bool:
        if self._raises:
            raise RuntimeError("Domain unbekannt")
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
    """Aeltere Systeme kennen den Schalter nicht - das ist kein Fehler."""
    info = await device_info(FakeLockdown(dev_mode_raises=True))
    assert info.developer_mode is False


@pytest.mark.asyncio
async def test_device_info_renders_warning_when_developer_mode_off():
    text = str(await device_info(FakeLockdown(dev_mode=False)))
    assert "AUS" in text


@pytest.mark.asyncio
async def test_service_provider_closes_lockdown(monkeypatch):
    fake = FakeLockdown()

    async def fake_connect(udid=None, timeout=0.0):
        return fake

    monkeypatch.setattr("modstaller.device.connection.connect", fake_connect)
    async with ServiceProvider() as sp:
        assert sp.udid == VALUES["UniqueDeviceID"]
    assert fake.closed, "lockdown muss geschlossen werden"


@pytest.mark.asyncio
async def test_list_devices_is_empty_without_usbmuxd():
    """usbmuxd ist socket-aktiviert: ohne iPhone laeuft es gar nicht.
    Das darf keine Ausnahme werfen, sondern nur eine leere Liste ergeben."""
    from modstaller.device.connection import list_devices
    assert isinstance(await list_devices(), list)
