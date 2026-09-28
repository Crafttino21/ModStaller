#!/usr/bin/env python3
"""Sets the version number everywhere it appears.

    packaging/set-version.py 0.2.0

The GUI (package.json) determines what electron-updater compares; the
backend (pyproject.toml) shows the same number in the system check. Both
must match, otherwise the app offers an update it already has.
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
        print("Usage: set-version.py X.Y.Z  (optionally -beta.1 or similar)", file=sys.stderr)
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
        print("pyproject.toml: no version line found", file=sys.stderr)
        return 1
    py.write_text(text)

    print(f"Version set to {version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
