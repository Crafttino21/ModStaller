"""Der Systemcheck liefert Daten - drucken ist Sache von CLI und Oberflaeche."""

from __future__ import annotations

import pytest

from modstaller import config, doctor
from modstaller.doctor import PROBLEM, TODO, Check


class FakeAnisette:
    """Weder Netz noch Emulation - beides gehoert nicht in einen Unittest."""

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
              Check("Apple-Anmeldung", False, kind=TODO),
              Check("CA", True)]
    assert [c.label for c in doctor.problems(checks)] == ["zsign"]
    assert [c.label for c in doctor.todos(checks)] == ["Apple-Anmeldung"]


def test_windows_checks_the_apple_device_service(monkeypatch):
    """Unter Windows gibt es kein usbmuxd - der Apple-Geraetedienst ersetzt ihn."""
    import socket

    class Conn:
        def close(self):
            pass

    monkeypatch.setattr(socket, "create_connection", lambda addr, timeout: Conn())
    c = doctor._usb_service_check(posix=False)
    assert c.ok and c.label == "Apple device service"


async def test_the_anisette_check_names_the_configured_source(
        monkeypatch, no_anisette, no_devices):
    """Welche Quelle gilt, entscheiden die Einstellungen - nicht der Check."""
    monkeypatch.setattr(config.Settings, "load", classmethod(
        lambda cls, path=None: cls(anisette_provider="remote",
                                   anisette_server="https://ani.example")))

    checks = await doctor.run_checks()

    assert any(c.label == "Anisette (server: https://ani.example)" and c.ok
               for c in checks)


async def test_a_broken_anisette_source_is_a_check_and_not_an_exception(
        monkeypatch, no_devices):
    """Unter Windows wirft LocalProvider - das muss eine Zeile bleiben."""
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
