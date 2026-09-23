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
