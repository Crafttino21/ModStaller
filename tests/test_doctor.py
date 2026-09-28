"""The system check returns data - printing is up to the CLI and interface."""

from __future__ import annotations

import pytest

from modstaller import config, doctor
from modstaller.doctor import PROBLEM, TODO, Check


class FakeAnisette:
    """Neither network nor emulation - neither belongs in a unit test."""

    name = "fake"

    def __init__(self, info="com.apple.akd/1.0"):
        self._info = info

    def client_info(self):
        return self._info


@pytest.fixture
def no_anisette(monkeypatch):
    monkeypatch.setattr("modstaller.apple.anisette.build",
                        lambda provider, server="": FakeAnisette())


@pytest.fixture
def no_devices(monkeypatch):
    async def none():
        return []
    monkeypatch.setattr("modstaller.device.connection.list_devices", none)


async def test_checks_are_data_and_print_nothing(capsys, no_anisette, no_devices):
    checks = await doctor.run_checks()

    assert capsys.readouterr().out == ""
    assert all(isinstance(c, Check) for c in checks)
    phone = next(c for c in checks if c.label == "iPhone detected")
    assert not phone.ok and phone.kind == TODO and phone.hint


def test_open_steps_are_not_problems():
    checks = [Check("zsign", False, kind=PROBLEM),
              Check("Apple sign-in", False, kind=TODO),
              Check("CA", True)]
    assert [c.label for c in doctor.problems(checks)] == ["zsign"]
    assert [c.label for c in doctor.todos(checks)] == ["Apple sign-in"]


def test_windows_checks_the_apple_device_service(monkeypatch):
    """Windows has no usbmuxd - the Apple device service replaces it."""
    import socket

    class Conn:
        def close(self):
            pass

    monkeypatch.setattr(socket, "create_connection", lambda addr, timeout: Conn())
    c = doctor._usb_service_check(posix=False)
    assert c.ok and c.label == "Apple device service"


async def test_the_anisette_check_names_the_configured_source(
        monkeypatch, no_anisette, no_devices):
    """The settings decide which source applies - not the check."""
    monkeypatch.setattr(config.Settings, "load", classmethod(
        lambda cls, path=None: cls(anisette_provider="remote",
                                   anisette_server="https://ani.example")))

    checks = await doctor.run_checks()

    assert any(c.label == "Anisette (server: https://ani.example)" and c.ok
               for c in checks)


async def test_a_broken_anisette_source_is_a_check_and_not_an_exception(
        monkeypatch, no_devices):
    """On Windows LocalProvider raises - that must stay a single line."""
    def boom(provider, server=""):
        raise RuntimeError("emulation does not run here")
    monkeypatch.setattr("modstaller.apple.anisette.build", boom)

    checks = await doctor.run_checks()

    bad = next(c for c in checks if c.label.startswith("Anisette"))
    assert not bad.ok and "emulation" in bad.detail


def test_windows_without_apple_devices_app_gets_a_hint(monkeypatch):
    import socket

    def refused(addr, timeout):
        raise ConnectionRefusedError()

    monkeypatch.setattr(socket, "create_connection", refused)
    c = doctor._usb_service_check(posix=False)
    assert not c.ok and "Apple Devices" in c.hint
