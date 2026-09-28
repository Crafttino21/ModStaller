"""The Windows post-processing step: Control Flow Guard out of the program.

Why it is needed is explained in ``packaging/build_backend.py``. This only
checks that it happens reliably - and that no other byte is touched: behind
the header the file carries the entire PyInstaller archive.
"""

from __future__ import annotations

import importlib.util
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_backend", ROOT / "packaging" / "build_backend.py")
build_backend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_backend)

PE_OFF = 0x80
DLLCHARS = PE_OFF + 24 + 70


def make_pe(dllchars: int, trailer: bytes = b"PYI-ARCHIVE") -> bytes:
    """Just as much PE as clear_cfg reads - plus something behind it."""
    data = bytearray(DLLCHARS + 2)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, PE_OFF)
    data[PE_OFF:PE_OFF + 4] = b"PE" + bytes(2)
    struct.pack_into("<H", data, PE_OFF + 24, 0x20B)   # PE32+
    struct.pack_into("<H", data, DLLCHARS, dllchars)
    return bytes(data) + trailer


def test_the_guard_flag_is_removed(tmp_path):
    exe = tmp_path / "x.exe"
    exe.write_bytes(make_pe(0xC160))

    build_backend.clear_cfg(exe)

    after, = struct.unpack_from("<H", exe.read_bytes(), DLLCHARS)
    assert after == 0x8160


def test_nothing_else_in_the_file_changes(tmp_path):
    """The PyInstaller archive sits behind the header - it must stay intact."""
    exe = tmp_path / "x.exe"
    before = make_pe(0xC160)
    exe.write_bytes(before)

    build_backend.clear_cfg(exe)

    after = exe.read_bytes()
    assert len(after) == len(before)
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert differing == [DLLCHARS + 1]      # only the flag's upper byte


def test_a_file_without_the_flag_is_left_alone(tmp_path):
    exe = tmp_path / "x.exe"
    before = make_pe(0x8160)
    exe.write_bytes(before)

    build_backend.clear_cfg(exe)

    assert exe.read_bytes() == before


def test_something_that_is_not_a_program_is_refused(tmp_path):
    exe = tmp_path / "x.exe"
    exe.write_bytes(make_pe(0xC160).replace(b"PE" + bytes(2), b"XX" + bytes(2), 1))
    with pytest.raises(SystemExit):
        build_backend.clear_cfg(exe)


_smoke_spec = importlib.util.spec_from_file_location(
    "smoke_backend", ROOT / "packaging" / "smoke_backend.py")
smoke_backend = importlib.util.module_from_spec(_smoke_spec)
_smoke_spec.loader.exec_module(smoke_backend)


@pytest.mark.parametrize("service_up, reported, ok", [
    (False, "missing", True),   # CI runner without Apple Devices
    (False, "ok", False),       # listing broke before it connected
    (True, "ok", True),
    (True, "missing", False),
])
def test_smoke_catches_a_broken_windows_device_listing(monkeypatch, service_up,
                                                       reported, ok):
    class Sock:
        def close(self):
            pass

    def connect(addr, timeout):
        if not service_up:
            raise ConnectionRefusedError
        return Sock()
    monkeypatch.setattr(smoke_backend.socket, "create_connection", connect)
    assert smoke_backend._usb_path_ok({"usbService": reported},
                                      windows=True) is ok


def test_smoke_needs_the_usb_field_everywhere():
    assert not smoke_backend._usb_path_ok({}, windows=False)
    assert smoke_backend._usb_path_ok({"usbService": "ok"}, windows=False)


_cv_spec = importlib.util.spec_from_file_location(
    "check_version", ROOT / "packaging" / "check-version.py")
check_version = importlib.util.module_from_spec(_cv_spec)
_cv_spec.loader.exec_module(check_version)

#: The tags as they really are - including the two without a dot.
RELEASED = ["1.1.0-beta.3", "1.2.0", "1.2.1-beta.1", "1.2.1-beta.2",
            "1.2.1-beta.3", "1.2.1-beta.4", "1.2.1-beta4", "1.2.1-beta5"]


def test_versions_sort_like_electron_updater():
    order = ["1.2.0", "1.2.1-beta.2", "1.2.1-beta.10", "1.2.1-beta4",
             "1.2.1-beta5", "1.2.1-rc.1", "1.2.1", "1.10.0"]
    for a, b in zip(order, order[1:]):
        assert check_version.compare(a, b) < 0, f"{a} < {b}"
        assert check_version.compare(b, a) > 0


@pytest.mark.parametrize("version", ["1.2.0", "1.2.1-beta.4", "1.2.1-beta.3"])
def test_a_released_or_older_version_is_refused(version):
    assert check_version.check(version, RELEASED)


def test_beta5_without_a_dot_is_a_trap_that_is_named():
    """After "beta5", "beta.6" is older - the check says so and offers
    what really comes after it."""
    problems = check_version.check("1.2.1-beta.6", RELEASED)
    assert "nicht neuer als 1.2.1-beta5" in problems[0]
    for s in check_version.suggestions("1.2.1-beta5"):
        assert check_version.compare(s, "1.2.1-beta5") > 0
        assert not check_version.check(s, RELEASED)
    assert "1.2.1-rc.1" in check_version.suggestions("1.2.1-beta5")


@pytest.mark.parametrize("version", ["1.2.1-beta6", "1.3", "v1.3.0", "1.3.0-nightly.1"])
def test_only_the_release_scheme_is_accepted(version):
    assert "keine gueltige" in check_version.check(version, RELEASED)[0]


@pytest.mark.parametrize("version", ["1.2.1-rc.1", "1.2.1", "1.2.2-beta.1", "2.0.0"])
def test_newer_versions_pass(version):
    assert check_version.check(version, RELEASED) == []


def test_the_next_beta_is_suggested_after_a_proper_one():
    assert check_version.suggestions("1.3.0-beta.2")[0] == "1.3.0-beta.3"
