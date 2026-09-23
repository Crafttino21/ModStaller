"""Der Systemcheck liefert Daten - drucken ist Sache von CLI und Oberflaeche."""

from __future__ import annotations

from modstaller import doctor
from modstaller.doctor import PROBLEM, TODO, Check


async def test_checks_are_data_and_print_nothing(capsys, monkeypatch):
    async def no_devices():
        return []
    monkeypatch.setattr("modstaller.device.connection.list_devices", no_devices)

    checks = await doctor.run_checks()

    assert capsys.readouterr().out == ""
    assert all(isinstance(c, Check) for c in checks)
    phone = next(c for c in checks if c.label == "iPhone erkannt")
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
    assert c.ok and c.label == "Apple-Gerätedienst"


def test_windows_without_apple_devices_app_gets_a_hint(monkeypatch):
    import socket

    def refused(addr, timeout):
        raise ConnectionRefusedError()

    monkeypatch.setattr(socket, "create_connection", refused)
    c = doctor._usb_service_check(posix=False)
    assert not c.ok and "Apple-Geräte" in c.hint
