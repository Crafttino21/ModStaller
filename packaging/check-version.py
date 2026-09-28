#!/usr/bin/env python3
"""Checks a new version number before release.sh / release.bat use it.

    packaging/check-version.py 1.2.2-beta.1

Refuses what would break updates:

* a number that was already released;
* a number that is not *newer* than every released one. electron-updater
  compares by SemVer and never offers an older version - such a release
  would reach nobody;
* pre-releases other than ``-alpha.N``, ``-beta.N`` or ``-rc.N``. In SemVer
  ``beta5`` is one word and sorts *after* every ``beta.N`` - after
  ``1.2.1-beta5`` a ``1.2.1-beta.6`` would count as older.

Compared against the Git tags (``v*``, fetch them first) and the version in
gui/package.json. Exit 0: fine, 1: refused (the reason is printed), 2: usage.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: What a new release may be called.
STRICT = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$")
#: What SemVer accepts - old tags are compared by this.
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


def parse(version: str) -> tuple[tuple[int, int, int], list[str]] | None:
    m = SEMVER.match(version.strip())
    if not m:
        return None
    core = (int(m[1]), int(m[2]), int(m[3]))
    return core, (m[4].split(".") if m[4] else [])


def compare(a: str, b: str) -> int:
    """SemVer 2.0 precedence - like electron-updater: <0, 0 or >0."""
    x, y = parse(a), parse(b)
    if x is None or y is None:
        raise ValueError(f"not a version: {a if x is None else b}")
    if x[0] != y[0]:
        return (x[0] > y[0]) - (x[0] < y[0])
    xp, yp = x[1], y[1]
    if not xp or not yp:            # without a pre-release suffix = newer
        return (len(yp) > 0) - (len(xp) > 0)
    for p, q in zip(xp, yp):
        if p == q:
            continue
        if p.isdigit() and q.isdigit():
            return (int(p) > int(q)) - (int(p) < int(q))
        if p.isdigit() != q.isdigit():
            return -1 if p.isdigit() else 1   # numbers sort before words
        return (p > q) - (p < q)
    return (len(xp) > len(yp)) - (len(xp) < len(yp))


def suggestions(latest: str) -> list[str]:
    """What could come after ``latest`` - valid and really newer."""
    core, pre = parse(latest)
    x, y, z = core
    out: list[str] = []
    m = STRICT.match(latest.lstrip("v"))
    if pre and m and m[4]:
        out.append(f"{x}.{y}.{z}-{m[4]}.{int(m[5]) + 1}")
    elif pre:
        out.append(f"{x}.{y}.{z}-rc.1")
    if pre:
        out.append(f"{x}.{y}.{z}")
    out.append(f"{x}.{y}.{z + 1}-beta.1")
    out.append(f"{x}.{y}.{z + 1}")
    out.append(f"{x}.{y + 1}.0")
    # Only what really sorts after it - "beta5" can make a guess wrong.
    return [s for s in out if compare(s, latest) > 0]


def check(version: str, released: list[str]) -> list[str]:
    """Why ``version`` must not be used - empty if it is fine."""
    if not STRICT.match(version):
        return [f"{version!r} ist keine gueltige Versionsnummer. Erlaubt: "
                "X.Y.Z oder X.Y.Z-alpha.N / -beta.N / -rc.N "
                "(mit Punkt vor der Zahl: beta.5, nicht beta5)."]
    known = [v for v in released if parse(v) is not None]
    same = [v for v in known if compare(v, version) == 0]
    if same:
        return [f"{version} wurde schon veroeffentlicht ({', '.join(sorted(set(same)))})."]
    if not known:
        return []
    latest = max(known, key=_Key)
    if compare(version, latest) <= 0:
        return [f"{version} ist nicht neuer als {latest} - der Updater wuerde "
                "sie niemandem anbieten.",
                "Moeglich waeren z. B.: " + ", ".join(suggestions(latest))]
    return []


class _Key:
    """Sort key from :func:`compare`."""

    def __init__(self, v: str) -> None:
        self.v = v

    def __lt__(self, other: "_Key") -> bool:
        return compare(self.v, other.v) < 0


def released_versions() -> list[str]:
    tags = subprocess.run(["git", "tag", "-l", "v*"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout
    versions = [t.strip()[1:] for t in tags.splitlines() if t.strip()]
    try:
        pkg = json.loads((ROOT / "gui" / "package.json").read_text())
        versions.append(pkg["version"])
    except (OSError, ValueError, KeyError):
        pass
    return versions


def main() -> int:
    if len(sys.argv) != 2:
        print("Aufruf: check-version.py X.Y.Z", file=sys.stderr)
        return 2
    problems = check(sys.argv[1], released_versions())
    for line in problems:
        print(line, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
