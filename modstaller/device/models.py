"""Aus ``iPhone17,2`` wird "iPhone 16 Pro Max" - und die passende Bauform.

Die Namen stammen aus der Geraetetabelle von pymobiledevice3, die mit jeder
neuen Generation gepflegt wird. Die Bauform brauchen wir nur fuers Bild in der
Oberflaeche: Home-Button, Notch oder Dynamic Island.
"""

from __future__ import annotations

import re

HOME_BUTTON, NOTCH, ISLAND, IPAD = "home", "notch", "island", "ipad"

#: Neuere Geraete ohne Dynamic Island: die "e"-Modelle erben das Gehaeuse
#: mit Notch. Alles andere ab iPhone15,2 (14 Pro) hat eine Island.
_NOTCH_LATE = frozenset({"iPhone17,5", "iPhone18,5"})

#: Home-Button trotz neuer Nummer: die SE-Modelle im iPhone-8-Gehaeuse.
_HOME_LATE = frozenset({"iPhone12,8", "iPhone14,6"})

#: Varianten, die fuer den Menschen dasselbe Geraet sind.
_VARIANT = re.compile(r"\s*\((Global|GSM|CDMA|China|WiFi|Cellular)\)$")


def _numbers(product_type: str) -> tuple[int, int] | None:
    m = re.match(r"^[A-Za-z]+(\d+),(\d+)$", product_type)
    return (int(m.group(1)), int(m.group(2))) if m else None


def marketing_name(product_type: str) -> str:
    try:
        from pymobiledevice3.irecv_devices import IRECV_DEVICES
    except ImportError:
        return product_type
    for d in IRECV_DEVICES:
        if d.product_type == product_type:
            return _VARIANT.sub("", d.display_name)
    return product_type


def form_factor(product_type: str) -> str:
    if product_type.startswith("iPad"):
        return IPAD
    nums = _numbers(product_type)
    if nums is None or not product_type.startswith("iPhone"):
        return ISLAND
    if product_type in _HOME_LATE:
        return HOME_BUTTON
    if product_type in _NOTCH_LATE:
        return NOTCH
    # iPhone10,3/10,6 ist das iPhone X - die erste Notch.
    if nums < (10, 3) or product_type in ("iPhone10,4", "iPhone10,5"):
        return HOME_BUTTON
    if nums < (15, 2):
        return NOTCH
    return ISLAND
