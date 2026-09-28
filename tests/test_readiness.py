"""The iPhone check: what it reports and what it tries to fix itself.

No real iPhone - device, profiles and AMFI are mocked. What is tested is the
decision, not pymobiledevice3.
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
    """An iPhone with configurable iOS, Developer Mode and profiles."""
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
    assert checks["ddi"].state == rd.OK   # mountable without Developer Mode


async def test_too_old_ios_is_flagged(phone):
    phone["info"] = _device("11.4", False)
    assert _by_id(await rd.run_checks())["ios"].state == rd.BAD


async def test_full_slots_warn_and_expired_profiles_can_be_cleaned(phone):
    phone["profiles"] = [Profile(5, "a"), Profile(5, "b"), Profile(5, "c"),
                         Profile(-1, "old")]
    c = _by_id(await rd.run_checks())["profiles"]
    assert c.state == rd.WARN
    assert c.fix == rd.FIX_EXPIRED_PROFILES
    assert "3 active" in c.detail and "1 expired" in c.detail


async def test_low_space_warns(phone):
    phone["sp"] = FakeSP(FakeLockdown(free=300_000_000))
    assert _by_id(await rd.run_checks())["space"].state == rd.WARN


async def test_no_device_means_no_checks(monkeypatch):
    class Gone:
        async def __aenter__(self):
            raise DeviceNotFound("gone")

        async def __aexit__(self, *exc):
            pass
    monkeypatch.setattr(rd, "ServiceProvider", lambda udid=None: Gone())
    assert await rd.run_checks() == []


async def test_untrusted_computer_offers_pairing(monkeypatch):
    class Untrusted:
        async def __aenter__(self):
            raise NotPaired("not paired")

        async def __aexit__(self, *exc):
            pass
    monkeypatch.setattr(rd, "ServiceProvider", lambda udid=None: Untrusted())
    [c] = await rd.run_checks()
    assert c.fix == rd.FIX_PAIR


async def test_locked_phone_asks_to_unlock_instead_of_pairing(monkeypatch):
    from pymobiledevice3.exceptions import PasswordRequiredError

    class Locked:
        async def __aenter__(self):
            raise NotPaired("locked") from PasswordRequiredError()

        async def __aexit__(self, *exc):
            pass
    monkeypatch.setattr(rd, "ServiceProvider", lambda udid=None: Locked())
    [c] = await rd.run_checks()
    assert c.fix is None and "Unlock" in c.manual


async def test_passcode_falls_back_to_revealing_the_switch(phone, monkeypatch):
    """With a passcode AMFI refuses - then at least reveal the switch."""
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
            assert enable_post_restart   # confirm the post-restart prompt too

    monkeypatch.setattr("pymobiledevice3.services.amfi.AmfiService", FakeAmfi)
    result = await rd.run_fix(rd.FIX_DEVELOPER_MODE)
    assert result.manual == ""


async def test_unknown_fix_is_refused(phone):
    with pytest.raises(Exception, match="Unknown fix"):
        await rd.run_fix("gibtsnicht")


# -- Mounting the Developer Disk Image -------------------------------------

from pymobiledevice3.exceptions import (  # noqa: E402
    AlreadyMountedError, MessageNotSupportedError, PyMobileDevice3Exception,
)
from pymobiledevice3.services import mobile_image_mounter  # noqa: E402

from modstaller.device import readiness  # noqa: E402
from modstaller.device.readiness import mount_developer_image  # noqa: E402
from modstaller.errors import DeviceError  # noqa: E402


class _Lockdown:
    def __init__(self, version: str):
        self.product_version = version


class _Provider:
    """Just enough ServiceProvider: a version and a tunnel."""

    TUNNEL = object()

    def __init__(self, version: str = "26.0"):
        self.lockdown = _Lockdown(version)

    async def rsd(self):
        return self.TUNNEL


def _mounter(monkeypatch, *outcomes):
    """auto_mount that fails with ``outcomes`` in turn, then succeeds."""
    calls = []
    pending = list(outcomes)

    async def fake(provider):
        calls.append(provider)
        if pending:
            raise pending.pop(0)

    monkeypatch.setattr(mobile_image_mounter, "auto_mount", fake)
    monkeypatch.setattr(readiness, "UNLOCK_POLL", 0.0)
    return calls


@pytest.mark.asyncio
async def test_locked_iphone_is_asked_to_unlock_and_retried(monkeypatch):
    """With the screen dark the service answers DeviceLocked - that is not
    a failure yet, just a wait."""
    calls = _mounter(monkeypatch, PyMobileDevice3Exception(
        "command MountImage failed with: {'Error': 'DeviceLocked'}"))
    said = []
    await mount_developer_image(_Provider(), said.append)
    assert len(calls) == 2
    assert any("unlock" in s for s in said)


@pytest.mark.asyncio
async def test_empty_refusal_during_the_queries_counts_as_locked(monkeypatch):
    """pymobiledevice3 turns DeviceLocked in the queries into an empty
    MessageNotSupportedError - that was the error message with nothing
    after the colon."""
    calls = _mounter(monkeypatch, MessageNotSupportedError())
    await mount_developer_image(_Provider())
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_staying_locked_ends_with_a_clear_message(monkeypatch):
    _mounter(monkeypatch, *[MessageNotSupportedError()] * 1000)
    with pytest.raises(DeviceError, match="locked"):
        await mount_developer_image(_Provider(), unlock_wait=0.0)


@pytest.mark.asyncio
async def test_already_mounted_is_fine(monkeypatch):
    _mounter(monkeypatch, AlreadyMountedError())
    await mount_developer_image(_Provider())


@pytest.mark.asyncio
async def test_other_errors_are_not_waited_out_and_never_empty(monkeypatch):
    class Silent(Exception):
        pass

    calls = _mounter(monkeypatch, Silent())
    with pytest.raises(DeviceError, match="could not be mounted: Silent"):
        await mount_developer_image(_Provider())
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_mounting_goes_through_the_tunnel(monkeypatch):
    """From iOS 27 on pymobiledevice3 installs the image as a cryptex and
    refuses plain lockdown with RSDRequiredError. The tunnel works from
    iOS 17 on - so that is the one way."""
    calls = _mounter(monkeypatch)
    await mount_developer_image(_Provider("27.0"))
    assert calls == [_Provider.TUNNEL]


@pytest.mark.asyncio
async def test_old_ios_mounts_over_lockdown(monkeypatch):
    calls = _mounter(monkeypatch)
    provider = _Provider("16.7")
    await mount_developer_image(provider)
    assert calls == [provider.lockdown]
