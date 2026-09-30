"""Is there something newer in the store than what is installed?

Version strings in sources are anything but uniform ("1.10", "2.3b2",
"v1.13.2", "2024.05.1"). Compared are the numbers in them, part by part -
1.10 is newer than 1.9. When the numbers say nothing (equal, or none at
all), a different version string with a newer date counts as newer.
"""

from __future__ import annotations

import re

from .model import StoreApp

_NUM = re.compile(r"\d+")


def _numbers(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in _NUM.findall(version or ""))


def newer(installed: str, offered: str, *, installed_date: str = "",
          offered_date: str = "") -> bool:
    """Whether ``offered`` is a newer version than ``installed``."""
    if not offered or offered == installed:
        return False
    a, b = _numbers(installed), _numbers(offered)
    if a and b and a != b:
        # Pad so that 1.2 == 1.2.0.
        width = max(len(a), len(b))
        return b + (0,) * (width - len(b)) > a + (0,) * (width - len(a))
    return bool(offered_date and installed_date and offered_date > installed_date)


def available(records, lookup) -> list[dict]:
    """Installed store apps with a newer version on offer.

    ``lookup(bundle_id, source_url)`` finds the store entry
    (``Catalog.find``)."""
    out = []
    for rec in records:
        if not getattr(rec, "store_bundle_id", ""):
            continue
        app: StoreApp | None = lookup(rec.store_bundle_id, rec.store_source)
        if app is None or not newer(rec.store_version, app.version):
            continue
        out.append({"bundleId": rec.bundle_id, "name": rec.name,
                    "installed": rec.store_version, "offered": app.version,
                    "source": app.source_url, "storeBundleId": app.bundle_id,
                    "size": app.size})
    return out
