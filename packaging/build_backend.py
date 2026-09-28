#!/usr/bin/env python3
"""Builds the Python backend as a standalone program (PyInstaller).

    python packaging/build_backend.py --out packaging/out          # for the GUI
    python packaging/build_backend.py --out packaging/out --cli    # plus the CLI

Runs on Linux (in the builder container, see build-backend.sh) and on
Windows (GitHub runner) - which is why the PyInstaller parameters live only
here. Expects ModStaller and PyInstaller to be installed in the current
Python.

Result:
    <out>/backend/modstaller-backend[.exe]   onedir - starts fast, for the GUI
    <out>/cli/modstaller[.exe]               onefile - a single file to share

On Windows a post-processing step is added: :func:`clear_cfg` strips Control
Flow Guard from the finished programs. Without it the Anisette emulation
crashes - the reason is explained there.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
import tempfile
from pathlib import Path

#: What PyInstaller doesn't find by itself: dynamically loaded modules, data
#: files (Apple's CA chain, pymobiledevice3 resources), the native Unicorn
#: library of the Anisette emulation - and the package metadata from which
#: the system check and "version" read their numbers.
#:
#: The metadata recursively, not package by package: several dependencies
#: read their own version number at *import* time (pyimg4, for instance, via
#: ipsw_parser from pymobiledevice3). If such a dist-info is missing, a
#: PackageNotFoundError is raised - found during the first device check on a
#: real iPhone. "modstaller" as the root covers the whole tree.
#:
#: ``pytun_pmd3`` is a separate package, not a subpackage of pymobiledevice3 -
#: so it is not picked up by the latter's ``--collect-all``. It contains
#: ``wintun.dll``, without which on Windows *every* operation that needs the
#: RSD tunnel fails: listing apps, installing, JIT. From iOS 17 on, that is
#: everything. The error surfaced as PyInstallerImportError on the first real
#: device.
#:
#: ``quickjs`` (from quickjs-ng) is only imported when JIT starts, so it is
#: collected explicitly; ``jit_host.js`` comes along with ``--collect-data``.
COMMON = [
    "--noconfirm", "--clean",
    "--collect-submodules", "modstaller",
    "--collect-data", "modstaller",
    "--collect-all", "pymobiledevice3",
    "--collect-all", "pytun_pmd3",
    "--collect-all", "anisette",
    "--collect-all", "unicorn",
    "--collect-all", "quickjs",
    "--recursive-copy-metadata", "modstaller",
]

#: Windows only: pymobiledevice3 reaches the Apple device service through
#: ``osu.win_util``, which imports these lazily on the first device listing.
#: Left out, every listing fails - and looks exactly like "no iPhone"
#: (1.2.1-beta.4). The smoke test checks the path (``status``).
WINDOWS_HIDDEN = [
    "--hidden-import", "pymobiledevice3.osu.win_util",
    "--hidden-import", "win32security",
    "--hidden-import", "ifaddr",
]

ENTRY = """\
import sys
from modstaller.cli import main
sys.exit(main())
"""


#: IMAGE_DLLCHARACTERISTICS_GUARD_CF in the optional header. The flag lives
#: in the main EXE and applies to the *whole* process.
GUARD_CF = 0x4000


def clear_cfg(exe: Path) -> None:
    """Strips Control Flow Guard from a finished program.

    PyInstaller's bootloader is built with ``/guard:cf``. With CFG active,
    MSVC's ``longjmp`` checks every jump target against the CFG table - and
    Unicorn jumps out of JIT-generated code that has no entry there.
    Result: ``__fastfail`` (0xC0000409) in the middle of the Anisette
    emulation. No Python error, nothing to catch: the process is gone, and
    with it the GUI's backend.

    ``python.exe`` doesn't set the flag itself - which is why the same
    emulation always worked in development and never in the packaged build.
    Without the flag the program behaves like a regular installation.
    """
    data = bytearray(exe.read_bytes())
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if bytes(data[pe:pe + 4]) != b"PE" + bytes(2):
        raise SystemExit(f"{exe}: not a PE program")
    off = pe + 24 + 70          # DllCharacteristics in the optional header
    flags, = struct.unpack_from("<H", data, off)
    if not flags & GUARD_CF:
        print(f"CFG was not set: {exe}")
        return
    struct.pack_into("<H", data, off, flags & ~GUARD_CF)
    exe.write_bytes(bytes(data))
    check, = struct.unpack_from("<H", exe.read_bytes(), off)
    if check & GUARD_CF:
        raise SystemExit(f"{exe}: CFG could not be removed")
    print(f"CFG removed: {exe} (0x{flags:04x} -> 0x{check:04x})")


def build(out: Path, *, cli: bool) -> None:
    import PyInstaller.__main__ as pyinstaller

    work = Path(tempfile.mkdtemp(prefix="modstaller-build-"))
    entry = work / "entry.py"
    entry.write_text(ENTRY)

    def run(name: str, mode: str) -> Path:
        dist = work / f"dist-{name}"
        extra = WINDOWS_HIDDEN if sys.platform == "win32" else []
        pyinstaller.run([*COMMON, *extra, mode, "--console", "--name", name,
                         "--distpath", str(dist),
                         "--workpath", str(work / f"build-{name}"),
                         "--specpath", str(work), str(entry)])
        return dist

    out.mkdir(parents=True, exist_ok=True)

    windows = sys.platform == "win32"

    backend = out / "backend"
    shutil.rmtree(backend, ignore_errors=True)
    shutil.move(str(run("modstaller-backend", "--onedir") / "modstaller-backend"),
                str(backend))
    if windows:
        clear_cfg(backend / "modstaller-backend.exe")
    print(f"Backend: {backend}")

    if cli:
        exe = "modstaller.exe" if windows else "modstaller"
        target = out / "cli"
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir()
        shutil.move(str(run("modstaller", "--onefile") / exe), str(target / exe))
        if windows:
            clear_cfg(target / exe)
        print(f"CLI: {target / exe}")

    shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cli", action="store_true",
                   help="also build the CLI as a single file")
    args = p.parse_args()
    build(args.out.resolve(), cli=args.cli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
