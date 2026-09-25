"""Der Windows-Nachbearbeitungsschritt: Control Flow Guard aus dem Programm.

Warum das sein muss, steht in ``packaging/build_backend.py``. Hier steht nur,
dass es zuverlaessig passiert - und dass sonst kein Byte angefasst wird: die
Datei traegt hinter dem Header das ganze PyInstaller-Archiv.
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


def make_pe(dllchars: int, trailer: bytes = b"PYI-ARCHIV") -> bytes:
    """Gerade so viel PE, wie clear_cfg liest - plus etwas dahinter."""
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
    """Das PyInstaller-Archiv haengt hinter dem Header - es muss heil bleiben."""
    exe = tmp_path / "x.exe"
    before = make_pe(0xC160)
    exe.write_bytes(before)

    build_backend.clear_cfg(exe)

    after = exe.read_bytes()
    assert len(after) == len(before)
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert differing == [DLLCHARS + 1]      # nur das obere Byte des Flags


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
