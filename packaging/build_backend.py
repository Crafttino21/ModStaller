#!/usr/bin/env python3
"""Baut das Python-Backend als eigenstaendiges Programm (PyInstaller).

    python packaging/build_backend.py --out packaging/out          # fuer die GUI
    python packaging/build_backend.py --out packaging/out --cli    # zusaetzlich CLI

Laeuft unter Linux (im Builder-Container, siehe build-backend.sh) und unter
Windows (GitHub-Runner) - die PyInstaller-Parameter stehen deshalb nur hier.
Erwartet, dass ModStaller und PyInstaller im aktuellen Python installiert sind.

Ergebnis:
    <out>/backend/modstaller-backend[.exe]   onedir - startet schnell, fuer die GUI
    <out>/cli/modstaller[.exe]               onefile - eine Datei zum Weitergeben
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

#: Was PyInstaller nicht von selbst findet: dynamisch geladene Module,
#: Datendateien (Apples CA-Kette, pymobiledevice3-Ressourcen), die native
#: Unicorn-Bibliothek der Anisette-Emulation - und die Paket-Metadaten, aus
#: denen Systemcheck und "version" ihre Nummern lesen.
COMMON = [
    "--noconfirm", "--clean",
    "--collect-submodules", "modstaller",
    "--collect-data", "modstaller",
    "--collect-all", "pymobiledevice3",
    "--collect-all", "anisette",
    "--collect-all", "unicorn",
    "--copy-metadata", "modstaller",
    "--copy-metadata", "pymobiledevice3",
    "--copy-metadata", "anisette",
    "--copy-metadata", "cryptography",
]

ENTRY = """\
import sys
from modstaller.cli import main
sys.exit(main())
"""


def build(out: Path, *, cli: bool) -> None:
    import PyInstaller.__main__ as pyinstaller

    work = Path(tempfile.mkdtemp(prefix="modstaller-build-"))
    entry = work / "entry.py"
    entry.write_text(ENTRY)

    def run(name: str, mode: str) -> Path:
        dist = work / f"dist-{name}"
        pyinstaller.run([*COMMON, mode, "--console", "--name", name,
                         "--distpath", str(dist),
                         "--workpath", str(work / f"build-{name}"),
                         "--specpath", str(work), str(entry)])
        return dist

    out.mkdir(parents=True, exist_ok=True)

    backend = out / "backend"
    shutil.rmtree(backend, ignore_errors=True)
    shutil.move(str(run("modstaller-backend", "--onedir") / "modstaller-backend"),
                str(backend))
    print(f"Backend: {backend}")

    if cli:
        exe = "modstaller.exe" if sys.platform == "win32" else "modstaller"
        target = out / "cli"
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir()
        shutil.move(str(run("modstaller", "--onefile") / exe), str(target / exe))
        print(f"CLI: {target / exe}")

    shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cli", action="store_true",
                   help="zusaetzlich die CLI als einzelne Datei bauen")
    args = p.parse_args()
    build(args.out.resolve(), cli=args.cli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
