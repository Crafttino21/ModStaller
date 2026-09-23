"""Der iPhone-Check: was er meldet und was er selbst zu beheben versucht.

Ohne echtes iPhone - Geraet, Profile und AMFI sind nachgebildet. Geprueft
wird die Entscheidung, nicht pymobiledevice3.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from modstaller.device import readiness as rd
from modstaller.device.connection import DeviceInfo
from modstaller.errors import DeviceNotFound, NotPaired


class FakeLockdown:
    def __init__(self, free: int = 20_000_000_000):
        self.free = free

    async def get_value(self, domain=None, key=None):
        assert domain == "com.apple.disk_usage"
        return {"TotalDataAvailable": self.free}


class FakeSP:
    def __init__(self, lockdown=None):
        self.lockdown = lockdown or FakeLockdown()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass


class Profile:
    def __init__(self, days: float, uuid: str = "U"):
        self.plist = {"UUID": uuid, "Name": f"P{uuid}",
                      "ExpirationDate": datetime.now(timezone.utc)
                      + timedelta(days=days)}


def _device(ios: str, dev_mode: bool) -> DeviceInfo:
    return DeviceInfo(udid="X", name="iPhone", product_type="iPhone17,2",
                      ios_version=ios, build="B", developer_mode=dev_mode)


@pytest.fixture
def phone(monkeypatch):
    """Ein iPhone mit einstellbarem iOS, Entwicklermodus und Profilen."""
    state = {"info": _device("27.0", True), "profiles": [], "sp": FakeSP()}

    async def info(lockdown):
        return state["info"]

    async def profiles(sp):
        return state["profiles"]

    async def ddi(sp, major, *, ready):
        return rd.Check("ddi", "DDI", rd.OK if ready else rd.NA)

    monkeypatch.setattr(rd, "ServiceProvider", lambda udid=None: state["sp"])
    monkeypatch.setattr(rd, "device_info", info)
    monkeypatch.setattr(rd, "_profiles", profiles)
    monkeypatch.setattr(rd, "_ddi_check", ddi)
    return state


def _by_id(checks):
    return {c.id: c for c in checks}


async def test_developer_mode_off_offers_a_fix(phone):
    phone["info"] = _device("27.0", False)
    c = _by_id(await rd.run_checks())["developer-mode"]
    assert c.state == rd.BAD and c.fix == rd.FIX_DEVELOPER_MODE and c.manual


async def test_developer_mode_is_not_needed_before_ios_16(phone):
    phone["info"] = _device("15.7", False)
    checks = _by_id(await rd.run_checks())
    assert checks["developer-mode"].state == rd.NA
    assert checks["ddi"].state == rd.OK   # ohne Entwicklermodus ladbar


async def test_too_old_ios_is_flagged(phone):
    phone["info"] = _device("11.4", False)
    assert _by_id(await rd.run_checks())["ios"].state == rd.BAD


async def test_full_slots_warn_and_expired_profiles_can_be_cleaned(phone):
    phone["profiles"] = [Profile(5, "a"), Profile(5, "b"), Profile(5, "c"),
                         Profile(-1, "old")]
    c = _by_id(await rd.run_checks())["profiles"]
    assert c.state == rd.WARN
    assert c.fix == rd.FIX_EXPIRED_PROFILES
    assert "3 aktive" in c.detail and "1 abgelaufene" in c.detail


async def test_low_space_warns(phone):
    phone["sp"] = FakeSP(FakeLockdown(free=300_000_000))
    assert _by_id(await rd.run_checks())["space"].state == rd.WARN


async def test_no_device_means_no_checks(monkeypatch):
    class Gone:
        async def __aenter__(self):
            raise DeviceNotFound("weg")

        async def __aexit__(self, *exc):
            pass
    monkeypatch.setattr(rd, "ServiceProvider", lambda udid=None: Gone())
    assert await rd.run_checks() == []


async def test_untrusted_computer_offers_pairing(monkeypatch):
    class Untrusted:
        async def __aenter__(self):
            raise NotPaired("nicht gepairt")

        async def __aexit__(self, *exc):
            pass
    monkeypatch.setattr(rd, "ServiceProvider", lambda udid=None: Untrusted())
    [c] = await rd.run_checks()
    assert c.fix == rd.FIX_PAIR


async def test_locked_phone_asks_to_unlock_instead_of_pairing(monkeypatch):
    from pymobiledevice3.exceptions import PasswordRequiredError

    class Locked:
        async def __aenter__(self):
            raise NotPaired("gesperrt") from PasswordRequiredError()

        async def __aexit__(self, *exc):
            pass
    monkeypatch.setattr(rd, "ServiceProvider", lambda udid=None: Locked())
    [c] = await rd.run_checks()
    assert c.fix is None and "entsperren" in c.manual


async def test_passcode_falls_back_to_revealing_the_switch(phone, monkeypatch):
    """Mit Code-Sperre verweigert AMFI - dann wenigstens den Schalter zeigen."""
    from pymobiledevice3.exceptions import DeviceHasPasscodeSetError
    calls = []

    class FakeAmfi:
        def __init__(self, lockdown):
            pass

        async def enable_developer_mode(self, enable_post_restart=True):
            calls.append("enable")
            raise DeviceHasPasscodeSetError()

        async def reveal_developer_mode_option_in_ui(self):
            calls.append("reveal")

    monkeypatch.setattr("pymobiledevice3.services.amfi.AmfiService", FakeAmfi)
    result = await rd.run_fix(rd.FIX_DEVELOPER_MODE)
    assert calls == ["enable", "reveal"]
    assert result.manual == rd.DEVELOPER_MODE_HINT


async def test_developer_mode_without_passcode_is_fully_automatic(phone, monkeypatch):
    class FakeAmfi:
        def __init__(self, lockdown):
            pass

        async def enable_developer_mode(self, enable_post_restart=True):
            assert enable_post_restart   # Nachfrage nach dem Neustart gleich mit

    monkeypatch.setattr("pymobiledevice3.services.amfi.AmfiService", FakeAmfi)
    result = await rd.run_fix(rd.FIX_DEVELOPER_MODE)
    assert result.manual == ""


async def test_unknown_fix_is_refused(phone):
    with pytest.raises(Exception, match="Unbekannte"):
        await rd.run_fix("gibtsnicht")
