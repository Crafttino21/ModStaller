#!/usr/bin/env python3
"""Setzt die Versionsnummer ueberall, wo sie steht.

    packaging/set-version.py 0.2.0

Die Oberflaeche (package.json) bestimmt, was electron-updater vergleicht; das
Backend (pyproject.toml) zeigt dieselbe Nummer im Systemcheck. Beide muessen
stimmen, sonst bietet die App ein Update an, das sie schon hat.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")


def main() -> int:
    if len(sys.argv) != 2 or not SEMVER.match(sys.argv[1]):
        print("Aufruf: set-version.py X.Y.Z  (optional -beta.1 o. ae.)", file=sys.stderr)
        return 2
    version = sys.argv[1]

    pkg = ROOT / "gui" / "package.json"
    data = json.loads(pkg.read_text())
    data["version"] = version
    pkg.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lock = ROOT / "gui" / "package-lock.json"
    data = json.loads(lock.read_text())
    data["version"] = version
    data.get("packages", {}).get("", {})["version"] = version
    lock.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    py = ROOT / "pyproject.toml"
    text, n = re.subn(r'(?m)^version = "[^"]*"$', f'version = "{version}"',
                      py.read_text(), count=1)
    if n != 1:
        print("pyproject.toml: keine version-Zeile gefunden", file=sys.stderr)
        return 1
    py.write_text(text)

    print(f"Version {version} gesetzt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
