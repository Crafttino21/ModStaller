"""Turns ``iPhone17,2`` into "iPhone 16 Pro Max" - and the matching form
factor.

The names come from pymobiledevice3's device table, which is kept up to date
with every new generation. We only need the form factor for the picture in
the UI: home button, notch, Dynamic Island - or an iPad, an iPod touch, a
TV for the Apple TV and a headset for the Vision Pro.
"""

from __future__ import annotations

import re

HOME_BUTTON, NOTCH, ISLAND, IPAD, TV = "home", "notch", "island", "ipad", "tv"
IPOD, VISION = "ipod", "vision"

#: Newer devices without a Dynamic Island: the "e" models inherit the
#: notched body. Everything else from iPhone15,2 (14 Pro) on has an island.
_NOTCH_LATE = frozenset({"iPhone17,5", "iPhone18,5"})

#: Home button despite a new number: the SE models in the iPhone 8 body.
_HOME_LATE = frozenset({"iPhone12,8", "iPhone14,6"})

#: Variants that are the same device as far as a human is concerned.
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


def device_kind(product_type: str) -> str:
    """What a person calls it - for log lines and messages."""
    for prefix, kind in (("iPad", "iPad"), ("iPod", "iPod touch"), ("AppleTV", "Apple TV"),
                         ("RealityDevice", "Apple Vision Pro")):
        if product_type.startswith(prefix):
            return kind
    return "iPhone"


def form_factor(product_type: str) -> str:
    if product_type.startswith("AppleTV"):
        return TV
    if product_type.startswith("RealityDevice"):
        return VISION
    if product_type.startswith("iPod"):
        return IPOD
    if product_type.startswith("iPad"):
        return IPAD
    nums = _numbers(product_type)
    if nums is None or not product_type.startswith("iPhone"):
        return ISLAND
    if product_type in _HOME_LATE:
        return HOME_BUTTON
    if product_type in _NOTCH_LATE:
        return NOTCH
    # iPhone10,3/10,6 is the iPhone X - the first notch.
    if nums < (10, 3) or product_type in ("iPhone10,4", "iPhone10,5"):
        return HOME_BUTTON
    if nums < (15, 2):
        return NOTCH
    return ISLAND
