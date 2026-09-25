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

Unter Windows kommt ein Nachbearbeitungsschritt dazu: :func:`clear_cfg` nimmt
Control Flow Guard aus den fertigen Programmen heraus. Ohne das stuerzt die
Anisette-Emulation ab - der Grund steht dort.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
import tempfile
from pathlib import Path

#: Was PyInstaller nicht von selbst findet: dynamisch geladene Module,
#: Datendateien (Apples CA-Kette, pymobiledevice3-Ressourcen), die native
#: Unicorn-Bibliothek der Anisette-Emulation - und die Paket-Metadaten, aus
#: denen Systemcheck und "version" ihre Nummern lesen.
#:
#: Die Metadaten rekursiv, nicht Paket fuer Paket: mehrere Abhaengigkeiten
#: lesen beim *Import* ihre eigene Versionsnummer (pyimg4 etwa, ueber
#: ipsw_parser aus pymobiledevice3). Fehlt so ein dist-info, fliegt eine
#: PackageNotFoundError - gefunden beim ersten Geraetecheck an einem echten
#: iPhone. "modstaller" als Wurzel deckt den ganzen Baum ab.
#:
#: ``pytun_pmd3`` ist ein eigenes Paket, kein Unterpaket von pymobiledevice3 -
#: es faellt deshalb nicht mit dessen ``--collect-all`` ab. Darin steckt
#: ``wintun.dll``, ohne die unter Windows *jeder* Zugriff scheitert, der den
#: RSD-Tunnel braucht: Apps auflisten, installieren, JIT. Ab iOS 17 ist das
#: alles. Der Fehler kam als PyInstallerImportError beim ersten echten Geraet.
COMMON = [
    "--noconfirm", "--clean",
    "--collect-submodules", "modstaller",
    "--collect-data", "modstaller",
    "--collect-all", "pymobiledevice3",
    "--collect-all", "pytun_pmd3",
    "--collect-all", "anisette",
    "--collect-all", "unicorn",
    "--recursive-copy-metadata", "modstaller",
]

ENTRY = """\
import sys
from modstaller.cli import main
sys.exit(main())
"""


#: IMAGE_DLLCHARACTERISTICS_GUARD_CF im Optional Header. Der Schalter steht in
#: der Haupt-EXE und gilt fuer den *ganzen* Prozess.
GUARD_CF = 0x4000


def clear_cfg(exe: Path) -> None:
    """Nimmt Control Flow Guard aus einem fertig gebauten Programm heraus.

    PyInstallers Bootloader ist mit ``/guard:cf`` gebaut. Ist CFG aktiv, prueft
    MSVCs ``longjmp`` jedes Sprungziel gegen die CFG-Tabelle - und Unicorn
    springt aus JIT-erzeugtem Code heraus, fuer den es dort keinen Eintrag gibt.
    Ergebnis: ``__fastfail`` (0xC0000409) mitten in der Anisette-Emulation. Kein
    Python-Fehler, nichts zum Abfangen: der Prozess ist weg und mit ihm das
    Backend der Oberflaeche.

    ``python.exe`` setzt den Schalter selbst nicht - deshalb lief dieselbe
    Emulation in der Entwicklung immer und im gepackten Build nie. Ohne ihn
    verhaelt sich das Programm wie eine gewoehnliche Installation.
    """
    data = bytearray(exe.read_bytes())
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if bytes(data[pe:pe + 4]) != b"PE" + bytes(2):
        raise SystemExit(f"{exe}: kein PE-Programm")
    off = pe + 24 + 70          # DllCharacteristics im Optional Header
    flags, = struct.unpack_from("<H", data, off)
    if not flags & GUARD_CF:
        print(f"CFG war nicht gesetzt: {exe}")
        return
    struct.pack_into("<H", data, off, flags & ~GUARD_CF)
    exe.write_bytes(bytes(data))
    check, = struct.unpack_from("<H", exe.read_bytes(), off)
    if check & GUARD_CF:
        raise SystemExit(f"{exe}: CFG liess sich nicht entfernen")
    print(f"CFG entfernt: {exe} (0x{flags:04x} -> 0x{check:04x})")


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
                   help="zusaetzlich die CLI als einzelne Datei bauen")
    args = p.parse_args()
    build(args.out.resolve(), cli=args.cli)
    return 0


if __name__ == "__main__":
    sys.exit(main())
